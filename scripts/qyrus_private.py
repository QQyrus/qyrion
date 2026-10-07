"""Capture Qyrion JSON output with exact-value redaction and private local logs.

Example:
    python3 qyrus_private.py --redact-file /private/test-values.json \
        --message-file /private/objective.txt -- run --platform web --jsonl

Use the same redact file for subsequent history/result commands. This wrapper
does not sanitize remote history, screenshots, downloads, or image artifacts.
An uncatchable process/host crash may leave its mode-0700 temporary log folder.
"""

from __future__ import annotations

import argparse
import codecs
import json
import math
import os
from pathlib import Path
import queue
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time

from qyrus_env import SetupError, load_environment


MAX_PRIVATE_BYTES = 1024 * 1024
MAX_FRAME_BYTES = 1024 * 1024
KEY_ALIASES = ("X-API-Key", "QYRUS_API_KEY", "QYRION_API_KEY")


def read_private(path: str) -> str:
    """Read bounded UTF-8 from an owned mode-0600 regular file without symlinks.

    Example:
        message = read_private("/private/objective.txt")
    """
    descriptor = None
    try:
        selected = Path(path).expanduser()
        if selected.is_symlink():
            raise SetupError("Private input must not be a symlink.")
        descriptor = os.open(selected, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                             | getattr(os, "O_NONBLOCK", 0))
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SetupError("Private input must be a regular file.")
        if os.name == "posix" and (stat.S_IMODE(metadata.st_mode) != 0o600
                                   or metadata.st_uid != os.getuid()):
            raise SetupError("Private input must be owned by you with mode 600.")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            content = handle.read(MAX_PRIVATE_BYTES + 1)
        if len(content) > MAX_PRIVATE_BYTES:
            raise SetupError("Private input exceeds the size limit.")
        return content.decode("utf-8")
    except SetupError:
        raise
    except (OSError, UnicodeError, ValueError):
        raise SetupError("Cannot read private input; check its path, permissions and encoding.") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def read_secrets(path: str) -> list[str]:
    """Read an array of exact target-test credentials, rejecting unusable shapes."""
    try:
        values = json.loads(read_private(path))
    except SetupError:
        raise
    except (ValueError, RecursionError):
        raise SetupError("Redact file must contain a JSON array of nonempty strings.") from None
    if (not isinstance(values, list) or not values or len(values) > 128
            or any(not isinstance(value, str) or not value or len(value) > 8192
                   for value in values)):
        raise SetupError("Redact file must contain 1 to 128 nonempty strings of at most 8192 characters.")
    return values


class Redactor:
    """Remove known exact strings and their JSON-escaped forms from output."""

    def __init__(self, values: list[str]) -> None:
        """Build longest-first patterns without storing secrets in diagnostic text."""
        patterns = {form for value in values if value for form in
                    (value, json.dumps(value, ensure_ascii=True)[1:-1],
                     json.dumps(value, ensure_ascii=False)[1:-1])}
        self.pattern = re.compile("|".join(re.escape(value) for value in
                                         sorted(patterns, key=len, reverse=True)))
        self.marker = "" if self.pattern.search("[REDACTED]") else "[REDACTED]"

    def text(self, value: str) -> str:
        """Redact a decoded string including embedded serialized JSON values."""
        return self.pattern.sub(lambda match: self.marker, value)

    def payload(self, value: object) -> object:
        """Redact keys, string values and matching numeric values recursively."""
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, dict):
            return {self.text(key): self.payload(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.payload(item) for item in value]
        if value is not None and self.text(str(value)) != str(value):
            return self.marker
        return value


class PrivateParser(argparse.ArgumentParser):
    """Prevent argparse from echoing unknown or malformed secret-bearing inputs."""

    def error(self, message: str) -> None:
        """Exit with safe generic usage text instead of echoing parser input."""
        self.exit(2, "Invalid private CLI arguments; see --help.\n")


class JsonOutput:
    """Buffer bounded complete JSON frames; suppress all unrecognized output."""

    def __init__(self, destination: object, redactor: Redactor) -> None:
        """Set up an incremental UTF-8 decoder for arbitrary child chunk splits."""
        self.destination = destination
        self.redactor = redactor
        self.decoder = codecs.getincrementaldecoder("utf-8")()
        self.pending = ""
        self.frame = ""
        self.disabled = False
        self.warned = False

    def suppress(self) -> None:
        """Emit a generic JSON notice once, without showing any child text."""
        if not self.warned:
            self.emit({"private_output_suppressed": True})
            self.warned = True

    def emit(self, payload: object) -> None:
        """Write one sanitized valid JSON record and flush for live consumers."""
        serialized = json.dumps(self.redactor.payload(payload), ensure_ascii=True,
                                allow_nan=False)
        self.destination.write(serialized + "\n")
        self.destination.flush()

    def line(self, value: str) -> None:
        """Combine pretty JSON lines or sanitize a complete JSONL record."""
        if not self.frame and not value.strip():
            return
        if not self.frame and value.lstrip()[:1] not in ("{", "["):
            self.suppress()
            return
        self.frame += value + "\n"
        if len(self.frame.encode("utf-8")) > MAX_FRAME_BYTES:
            self.disabled = True
            self.frame = ""
            self.suppress()
            return
        try:
            payload = json.loads(self.frame)
        except (ValueError, RecursionError):
            return
        self.frame = ""
        try:
            self.emit(payload)
        except (ValueError, RecursionError):
            self.suppress()

    def feed(self, chunk: bytes, *, final: bool = False) -> None:
        """Preserve frame boundaries across chunks and suppress invalid UTF-8."""
        if self.disabled:
            return
        try:
            self.pending += self.decoder.decode(chunk, final=final)
        except UnicodeError:
            self.disabled = True
            self.suppress()
            return
        while "\n" in self.pending and not self.disabled:
            value, self.pending = self.pending.split("\n", 1)
            self.line(value)
        if len(self.pending.encode("utf-8")) > MAX_FRAME_BYTES:
            self.disabled = True
            self.pending = ""
            self.suppress()
        if final and not self.disabled:
            if self.pending:
                self.line(self.pending)
            if self.frame:
                self.suppress()
            self.pending = self.frame = ""


def prepare_command(command: list[str], message: str | None, redactor: Redactor) -> list[str]:
    """Require machine output and route private messages to Qyrion stdin.

    Example:
        prepare_command(["sessions", "send", "run-1", "--jsonl"], text, redactor)
    """
    if not command or not any(flag in command for flag in ("--json", "--jsonl")):
        raise SetupError("Provide a Qyrion subcommand with --json or --jsonl after --.")
    if any(redactor.text(argument) != argument for argument in command):
        raise SetupError("Sensitive values must not appear in command arguments; use a private message file.")
    accepts_message = command[:1] == ["run"] or command[:2] in (
        ["sessions", "create"], ["sessions", "send"])
    if any(argument == "--message-file" or argument.startswith("--message-file=")
           for argument in command):
        raise SetupError("Use the wrapper's --message-file before --, not the child option.")
    if accepts_message and message is None:
        raise SetupError("This subcommand requires the wrapper's private --message-file.")
    if message is not None:
        if not accepts_message:
            raise SetupError("Private message input is supported only for run and sessions create/send.")
        command = [*command, "--message-file", "-"]
    return command


def stop_child(child: subprocess.Popen) -> None:
    """Terminate the child process group and escalate once, without retrying."""
    try:
        if os.name == "posix":
            os.killpg(child.pid, signal.SIGTERM)
        elif child.poll() is None:
            child.terminate()
        child.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        try:
            if os.name == "posix":
                os.killpg(child.pid, signal.SIGKILL)
            else:
                child.kill()
            child.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass


def capture(command: list[str], environment: dict[str, str], message: str | None,
            redactor: Redactor, timeout: float | None) -> int:
    """Stream sanitized child pipes while isolating/removing its execution logs.

    Child statuses are preserved; timeout and interruption return 124 and 130.
    The child never inherits the caller's stdout/stderr or objective-file path.
    """
    chunks = queue.Queue(maxsize=32)
    with tempfile.TemporaryDirectory(prefix="qyrus-private-") as log_dir:
        os.chmod(log_dir, 0o700)
        environment = {**environment, "QYRION_LOG_DIR": log_dir}
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=environment, shell=False,
                                 start_new_session=os.name == "posix")

        def read_pipe(pipe: object, index: int) -> None:
            """Queue bounded raw chunks internally, never writing them to the caller."""
            try:
                while chunk := os.read(pipe.fileno(), 4096):
                    chunks.put((index, chunk))
            except (OSError, ValueError):
                pass
            finally:
                chunks.put((index, None))

        def write_message() -> None:
            """Deliver the private objective only through stdin and then close it."""
            try:
                if message is not None:
                    child.stdin.write(message.encode("utf-8"))
                    child.stdin.flush()
            except (OSError, ValueError):
                pass
            finally:
                try:
                    child.stdin.close()
                except OSError:
                    pass

        outputs = [JsonOutput(sys.stdout, redactor), JsonOutput(sys.stderr, redactor)]
        readers = [threading.Thread(target=read_pipe, args=(pipe, index), daemon=True)
                   for index, pipe in enumerate((child.stdout, child.stderr))]
        for reader in readers:
            reader.start()
        threading.Thread(target=write_message, daemon=True).start()
        deadline = None if timeout is None else time.monotonic() + timeout
        completed = set()
        try:
            while len(completed) < 2:
                if deadline is not None and time.monotonic() >= deadline:
                    stop_child(child)
                    print(json.dumps({"private_command_timeout": True}), file=sys.stderr)
                    return 124
                try:
                    index, chunk = chunks.get(timeout=0.1)
                except queue.Empty:
                    continue
                if chunk is None:
                    completed.add(index)
                    outputs[index].feed(b"", final=True)
                else:
                    outputs[index].feed(chunk)
            remaining = None if deadline is None else max(0.001, deadline - time.monotonic())
            return child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            stop_child(child)
            print(json.dumps({"private_command_timeout": True}), file=sys.stderr)
            return 124
        except KeyboardInterrupt:
            stop_child(child)
            return 130
        finally:
            if child.poll() is None:
                stop_child(child)
            child.stdout.close()
            child.stderr.close()


def main() -> int:
    """Validate private inputs, load shared credentials, and capture one CLI call."""
    parser = PrivateParser(description=__doc__)
    parser.add_argument("--redact-file", required=True)
    parser.add_argument("--message-file")
    parser.add_argument("--env-file")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if not args.command or args.command[0] != "--":
            raise SetupError("Separate Qyrion subcommand arguments with --.")
        if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
            raise SetupError("Timeout must be a finite positive number of seconds.")
        values = read_secrets(args.redact_file)
        environment = load_environment(args.env_file)
        keys = [mapping[name] for mapping in (os.environ, environment)
                for name in KEY_ALIASES if mapping.get(name)]
        redactor = Redactor([*values, *keys])
        message = read_private(args.message_file) if args.message_file else None
        if message is not None and Redactor(keys).text(message) != message:
            raise SetupError("The Qyrus API key must never be included in a test objective.")
        command = prepare_command(args.command[1:], message, redactor)
        return capture([environment.get("QYRION_CLI", "qyrion"), *command],
                       environment, message, redactor, args.timeout)
    except SetupError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception:
        print("Private CLI capture failed; check inputs and CLI installation.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

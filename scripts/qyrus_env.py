"""Load one private Qyrus dotenv file without evaluating shell expressions.

Example:
    python3 qyrus_env.py configure --env-file ~/.config/qyrus/credentials.env
    python3 qyrus_env.py run -- qyrion capabilities --json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from qyrus_process import launch_command


class SetupError(ValueError):
    """Describe a configuration problem without disclosing file contents."""


def sdk_command() -> list[str]:
    """Return a uv-managed Python command that installs the pinned SDK if absent."""
    return ["uv", "run", "--quiet", "--isolated", "--no-project", "--python", "3.12",
            "--with", "qyrusai==1.0.9", "python"]


def ensure_sdk() -> None:
    """Prepare the cached SDK environment without making an authenticated API call.

    uv reuses the compatible cached environment or installs missing packages.
    Suppress installer details; failures must not expose private registry URLs.
    """
    try:
        result = subprocess.run(
            [*sdk_command(), "-c", "import qyrusai"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180,
        )
        if result.returncode:
            raise SetupError("QyrusAI installation failed. Check uv and package-index access, then rerun configure.")
    except (OSError, subprocess.TimeoutExpired):
        raise SetupError("QyrusAI installation could not finish. Ensure uv is installed and retry configure.") from None


def config_path() -> Path:
    """Return the user-owned path selector, outside the plugin cache."""
    return Path.home() / ".config/qyrus/plugin.json"


def resolve_env_file(explicit: str | None = None) -> Path:
    """Resolve explicit path, QYRUS_ENV_FILE, saved path, then the default file."""
    selected = explicit or os.environ.get("QYRUS_ENV_FILE")
    if not selected and config_path().exists():
        try:
            selected = json.loads(config_path().read_text())["env_file"]
            if not isinstance(selected, str) or not selected:
                raise ValueError
        except (OSError, ValueError, KeyError, TypeError):
            raise SetupError("Invalid Qyrus path selector; rerun configure --env-file <path>.") from None
    return Path(selected or "~/.config/qyrus/credentials.env").expanduser().resolve()


def read_values(path: Path) -> dict[str, str]:
    """Parse literal, single-line KEY=value entries; never source or interpolate.

    Accept hyphens (X-API-Key), optional export, and whole-value quotes.
    Reject duplicate keys and malformed lines without printing their contents.
    """
    try:
        with path.open(encoding="utf-8") as handle:
            mode = os.fstat(handle.fileno()).st_mode
            if not stat.S_ISREG(mode):
                raise SetupError("Qyrus credentials must be a regular file.")
            if os.name == "posix" and mode & 0o077:
                raise SetupError("Qyrus credentials must be private; run chmod 600 on the env file.")
            lines = handle.read().splitlines()
    except (OSError, UnicodeError):
        raise SetupError("Cannot read Qyrus credentials. Create a private .env and provide its path; see qyrus-setup.") from None
    values: dict[str, str] = {}
    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(.*)", line)
        if not match or match[1] in values:
            raise SetupError(f"Invalid or duplicate dotenv entry at line {number}.")
        key, value = match.groups()
        if value[:1] in ("'", '"'):
            if len(value) < 2 or value[-1] != value[0]:
                raise SetupError(f"Unclosed dotenv quote at line {number}.")
            value = value[1:-1]
        if "\x00" in value or "\r" in value or "\n" in value:
            raise SetupError(f"Invalid dotenv value at line {number}.")
        values[key] = value
    return values


def https_url(value: str) -> str:
    """Validate an explicit endpoint without including it in error messages."""
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == "https" and parts.hostname and not parts.username
                 and not parts.password and not parts.query and not parts.fragment
                 and not any(c.isspace() for c in value))
        if not valid:
            raise ValueError
        _ = parts.port
    except ValueError:
        raise SetupError("Qyrus endpoints must be HTTPS URLs without credentials, query, or fragment.") from None
    return value


def application_endpoints(value: str) -> tuple[str, str]:
    """Normalize a Qyrus tenant and derive its MCP endpoint.

    Example:
        >>> application_endpoints("app.qyrus.com")
        ('https://app.qyrus.com', 'https://app-mcp.qyrus.com/mcp')
    """
    url = https_url(value if "://" in value else "https://" + value)
    parts = urlsplit(url)
    match = re.fullmatch(r"([a-z0-9](?:[a-z0-9-]*[a-z0-9])?)\.qyrus\.com", parts.hostname or "")
    if not match or parts.path not in ("", "/") or parts.port is not None:
        raise SetupError("QYRION_APP_URL must be <env_name>.qyrus.com, without a port or application path.")
    tenant = match[1]
    return f"https://{tenant}.qyrus.com", f"https://{tenant}-mcp.qyrus.com/mcp"


def load_environment(explicit: str | None = None) -> dict[str, str]:
    """Map the selected file to CLI, SDK, and MCP variables in a child process.

    The file is authoritative: remove stale Qyrion credentials and service
    overrides from the inherited environment before copying supported values.
    """
    selected = resolve_env_file(explicit)
    values = read_values(selected)
    key = values.get("X-API-Key", "").strip()
    if not key or key.startswith("<") or key in {"...", "replace-me"}:
        raise SetupError("Set X-API-Key in the private env file; never paste it into chat.")
    if not values.get("QYRION_APP_URL"):
        raise SetupError("Set QYRION_APP_URL to your Qyrus URL in the private env file.")
    app_url, mcp_url = application_endpoints(values["QYRION_APP_URL"].strip())
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("QYRION_") and k not in {"QYRUS_API_KEY", "X-API-Key", "QYRUS_MCP_URL"}}
    env.update({"QYRION_API_KEY": key, "QYRUS_API_KEY": key})
    env["QYRUS_ENV_FILE"] = str(selected)
    for name in ("QYRION_TEAM_ID", "QYRION_USER_EMAIL"):
        if values.get(name):
            env[name] = values[name]
    env["QYRION_APP_URL"] = app_url
    tenant = urlsplit(app_url).hostname.split(".")[0]
    gateway = "https://gateway.qyrus.com" if tenant == "app" else f"https://{tenant}-gateway.qyrus.com"
    env["QYRION_TESTHUB_URL"] = gateway + "/df-ai-sessions-testhub-cli/v1"
    env["QYRION_RUNBRIDGE_URL"] = gateway + "/df-ai-sessions-runbridge-cli/v1"
    if os.environ.get("QYRION_CLI"):
        env["QYRION_CLI"] = os.environ["QYRION_CLI"]
    env["QYRUS_MCP_URL"] = mcp_url
    return env


def write_mcp_endpoint(path: Path, endpoint: str) -> None:
    """Add/update only the derived endpoint in the selected private env file.

    Preserve other entries and comments; atomically replace with mode 0600.
    Runtime always derives the URL again, so an old saved value cannot route
    a key to the wrong tenant after an application URL change.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    entry = f"QYRUS_MCP_URL={endpoint}"
    pattern = r"\s*(?:export\s+)?QYRUS_MCP_URL\s*="
    found = any(re.match(pattern, line) for line in lines)
    lines = [entry if re.match(pattern, line) else line for line in lines]
    if not found:
        lines.append(entry)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write("\n".join(lines) + "\n")
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_selection(path: Path) -> None:
    """Atomically save only the absolute env-file path, never credential values."""
    target = config_path()
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump({"env_file": str(path)}, handle)
        handle.write("\n")
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    """Validate setup, remember a path, or launch a credential-wrapped command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "configure", "run", "sdk"))
    parser.add_argument("--env-file")
    args, command = parser.parse_known_args()
    if command[:1] == ["--"]:
        command = command[1:]
    try:
        if args.action not in {"run", "sdk"} and command:
            raise SetupError("Unexpected arguments; see --help.")
        if args.action == "configure" and not args.env_file:
            raise SetupError("configure requires --env-file <path>.")
        env = load_environment(args.env_file)
        if args.action == "configure":
            ensure_sdk()
            selected = resolve_env_file(args.env_file)
            write_mcp_endpoint(selected, env["QYRUS_MCP_URL"])
            save_selection(selected)
        if args.action in {"run", "sdk"}:
            if not command:
                raise SetupError("run/sdk requires -- <command or Python script> [arguments].")
            if args.action == "sdk":
                command = [*sdk_command(), *command]
            elif command[0] == "qyrion":
                command[0] = env.get("QYRION_CLI", "qyrion")
            return launch_command(command, env)
        print(json.dumps({"configured": True, "api_key_present": True,
                          "application_url_present": bool(env.get("QYRION_APP_URL")),
                          "team_present": bool(env.get("QYRION_TEAM_ID")),
                          **({"sdk_ready": True} if args.action == "configure" else {})}))
        return 0
    except SetupError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError:
        print("Qyrus setup or command launch failed; check paths and executable installation.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

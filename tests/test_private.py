"""Verify private CLI capture offline with synthetic credentials and child pipes."""

import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import textwrap
import time

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import qyrus_private


@pytest.fixture
def inputs(tmp_path):
    """Create private synthetic inputs and a real fake CLI without remote calls."""
    secrets = ['demo"pass\\word\né', "demo@example.test"]
    key = "synthetic-only-qyrus-key"
    env_file = tmp_path / "credentials.env"
    env_file.write_text(f"X-API-Key={key}\nQYRION_APP_URL=stg.qyrus.com\nQYRION_TEAM_ID=fixture-team\n")
    redact_file = tmp_path / "values.json"
    redact_file.write_text(json.dumps(secrets))
    message_file = tmp_path / "objective.txt"
    message_file.write_text("Sign in as " + secrets[1] + " with " + secrets[0])
    for path in (env_file, redact_file, message_file):
        path.chmod(0o600)
    cli = tmp_path / "fake cli"
    cli.write_text("#!" + sys.executable + "\n" + textwrap.dedent('''
        import json, os, pathlib, stat, sys, time
        message = sys.stdin.read()
        secrets = json.loads(pathlib.Path(os.environ['TEST_REDACT_FILE']).read_text())
        logs = pathlib.Path(os.environ['QYRION_LOG_DIR'])
        assert stat.S_IMODE(logs.stat().st_mode) == 0o700
        (logs / 'execution.jsonl').write_text(message + '\\n' + secrets[0])
        pathlib.Path(os.environ['TEST_LOG_PATH']).write_text(str(logs))
        pathlib.Path(os.environ['TEST_LAUNCH_COUNT']).open('a').write('launch\\n')
        assert os.environ['QYRION_API_KEY'] == 'synthetic-only-qyrus-key'
        assert os.environ['QYRION_TEAM_ID'] == 'fixture-team'
        assert not any(value in argument for argument in sys.argv for value in secrets)
        if os.environ.get('TEST_SLEEP'):
            time.sleep(10)
        payload = {'content': message or secrets[0], 'objective_text': secrets[1],
                   'nested_json': json.dumps({'password': secrets[0]}),
                   'key': os.environ['QYRION_API_KEY'],
                   'stale': os.environ.get('TEST_STALE_KEY', ''), 'argv': sys.argv[1:]}
        encoded = json.dumps(payload, indent=2 if os.environ.get('TEST_PRETTY') else None)
        for value in encoded.encode('utf-8'):
            os.write(1, bytes([value]))
        os.write(1, b'\\n')
        print(json.dumps({'event': 'done', 'content': secrets[0]}), flush=True)
        print(json.dumps({'error': secrets[0], 'key': os.environ['QYRUS_API_KEY']}), file=sys.stderr, flush=True)
        print('Traceback: ' + secrets[0], file=sys.stderr, flush=True)
        raise SystemExit(int(os.environ.get('TEST_EXIT', '0')))
    '''))
    cli.chmod(0o700)
    return {"secrets": secrets, "key": key, "env": env_file, "redact": redact_file,
            "message": message_file, "cli": cli, "root": tmp_path}


def invoke(inputs, command, *, message=False, extras=(), environment=None):
    """Call the wrapper as a real process with only private input paths in argv."""
    args = [sys.executable, str(SCRIPTS / "qyrus_private.py"), "--env-file", str(inputs["env"]),
            "--redact-file", str(inputs["redact"]), *extras]
    if message:
        args += ["--message-file", str(inputs["message"])]
    env = {**os.environ, "QYRION_CLI": str(inputs["cli"]),
           "TEST_REDACT_FILE": str(inputs["redact"]),
           "TEST_LOG_PATH": str(inputs["root"] / "log-path"),
           "TEST_LAUNCH_COUNT": str(inputs["root"] / "launch-count"),
           **(environment or {})}
    return subprocess.run([*args, "--", *command], env=env, capture_output=True, text=True,
                          timeout=15)


def assert_clean(inputs, result):
    """Check raw/escaped secrets are absent and each emitted line is valid JSON."""
    combined = result.stdout + result.stderr
    for value in [*inputs["secrets"], inputs["key"]]:
        assert value not in combined
        assert json.dumps(value)[1:-1] not in combined
    for line in combined.splitlines():
        json.loads(line)
    log_path = Path((inputs["root"] / "log-path").read_text())
    assert not log_path.exists()


@pytest.mark.parametrize("command", [["run", "--jsonl"], ["sessions", "create", "--jsonl"],
                                    ["sessions", "send", "fixture-run", "--jsonl"]])
def test_private_message_commands_capture_all_output(inputs, command):
    """Deliver objectives via stdin, redact both streams, and remove private logs."""
    result = invoke(inputs, command, message=True, environment={"TEST_EXIT": "7"})
    assert result.returncode == 7
    assert_clean(inputs, result)
    payloads = [json.loads(line) for line in result.stdout.splitlines()]
    assert payloads[0]["argv"] == [*command, "--message-file", "-"]
    assert payloads[0]["content"] == "Sign in as [REDACTED] with [REDACTED]"
    assert payloads[1] == {"event": "done", "content": "[REDACTED]"}
    errors = [json.loads(line) for line in result.stderr.splitlines()]
    assert errors == [{"error": "[REDACTED]", "key": "[REDACTED]"},
                      {"private_output_suppressed": True}]
    assert (inputs["root"] / "launch-count").read_text() == "launch\n"


@pytest.mark.parametrize("subcommand", ["list", "show", "stream", "result", "steps", "save"])
def test_history_calls_reuse_redaction_with_pretty_json(inputs, subcommand):
    """Redact saved secret history without requiring a new message or remote call."""
    result = invoke(inputs, ["sessions", subcommand, "fixture-run", "--json"],
                    environment={"TEST_PRETTY": "1"})
    assert result.returncode == 0
    assert_clean(inputs, result)
    first = json.loads(result.stdout.splitlines()[0])
    assert first["nested_json"] == '{"password": "[REDACTED]"}'


def test_inherited_and_shared_qyrus_key_aliases_are_redacted(inputs):
    """Suppress stale inherited aliases as well as the authoritative loaded key."""
    stale = "synthetic-stale-key"
    result = invoke(inputs, ["sessions", "show", "fixture-run", "--json"],
                    environment={"X-API-Key": stale, "TEST_STALE_KEY": stale})
    assert result.returncode == 0
    assert_clean(inputs, result)
    assert stale not in result.stdout + result.stderr
    assert json.loads(result.stdout.splitlines()[0])["stale"] == "[REDACTED]"


def test_chunk_boundaries_and_unicode_json_escapes():
    """Redact JSON-decoded values split at every possible UTF-8/escape boundary."""
    secret = 'synthetic"\\\né'
    encoded = (json.dumps({"content": secret}, ensure_ascii=False) + "\n").encode()
    for offset in range(len(encoded) + 1):
        destination = io.StringIO()
        output = qyrus_private.JsonOutput(destination, qyrus_private.Redactor([secret]))
        output.feed(encoded[:offset])
        output.feed(encoded[offset:], final=True)
        assert json.loads(destination.getvalue()) == {"content": "[REDACTED]"}
    destination = io.StringIO()
    output = qyrus_private.JsonOutput(destination, qyrus_private.Redactor([secret]))
    output.feed(b'{"content":"synthetic\\u0022\\u005c\\u000a\\u00e9"}', final=True)
    assert json.loads(destination.getvalue()) == {"content": "[REDACTED]"}


@pytest.mark.parametrize("content", ["not-json", '"secret"', "[]", '[""]', '[42]', '{}', '["a", null]'])
def test_invalid_redact_files_never_echo_contents(inputs, content):
    """Reject invalid sensitive input shapes before launching a child."""
    inputs["redact"].write_text(content)
    result = invoke(inputs, ["sessions", "list", "--json"])
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert content not in result.stderr
    assert not (inputs["root"] / "launch-count").exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions and symlink contract")
@pytest.mark.parametrize("kind", ["public", "symlink", "directory", "oversized", "encoding"])
def test_unsafe_private_inputs_fail_closed(inputs, kind):
    """Reject broad permissions, links, nonfiles, oversized files and bad UTF-8."""
    path = inputs["redact"]
    if kind == "public":
        path.chmod(0o644)
    elif kind == "symlink":
        target = path.with_suffix(".target")
        path.rename(target)
        path.symlink_to(target)
    elif kind == "directory":
        path.unlink()
        path.mkdir()
    elif kind == "oversized":
        path.write_bytes(b"x" * (qyrus_private.MAX_PRIVATE_BYTES + 1))
    else:
        path.write_bytes(b"\xff")
    result = invoke(inputs, ["sessions", "list", "--json"])
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert not (inputs["root"] / "launch-count").exists()


@pytest.mark.parametrize("command,message", [(["run", "--jsonl"], False),
    (["sessions", "show", "fixture-run", "--json"], True),
    (["run", "--message-file", "-", "--jsonl"], True),
    (["sessions", "list"], False)])
def test_invalid_message_and_output_contracts_do_not_launch(inputs, command, message):
    """Require wrapper stdin and explicit machine output before child launch."""
    result = invoke(inputs, command, message=message)
    assert result.returncode == 2
    assert not (inputs["root"] / "launch-count").exists()


def test_known_sensitive_argv_and_qyrus_key_objective_are_rejected(inputs):
    """Keep exact test values out of argv and service authentication out of objectives."""
    result = invoke(inputs, ["run", inputs["secrets"][0], "--jsonl"], message=True)
    assert result.returncode == 2
    assert inputs["secrets"][0] not in result.stdout + result.stderr
    inputs["message"].write_text("Use " + inputs["key"])
    result = invoke(inputs, ["run", "--jsonl"], message=True)
    assert result.returncode == 2
    assert inputs["key"] not in result.stdout + result.stderr
    assert not (inputs["root"] / "launch-count").exists()


def test_timeout_removes_logs_and_never_retries(inputs):
    """Stop a stalled CLI and remove local secret logs with an explicit timeout."""
    result = invoke(inputs, ["run", "--jsonl"], message=True,
                    extras=["--timeout", "0.5"], environment={"TEST_SLEEP": "1"})
    assert result.returncode == 124
    assert result.stderr == '{"private_command_timeout": true}\n'
    assert not Path((inputs["root"] / "log-path").read_text()).exists()
    assert (inputs["root"] / "launch-count").read_text() == "launch\n"


@pytest.mark.skipif(os.name != "posix", reason="POSIX signal cleanup contract")
def test_interrupt_removes_logs_and_stops_child(inputs):
    """Interrupt a running wrapper and verify private execution logs are removed."""
    child = subprocess.Popen(
        [sys.executable, str(SCRIPTS / "qyrus_private.py"), "--env-file", str(inputs["env"]),
         "--redact-file", str(inputs["redact"]), "--message-file", str(inputs["message"]),
         "--", "run", "--jsonl"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "QYRION_CLI": str(inputs["cli"]), "TEST_SLEEP": "1",
             "TEST_REDACT_FILE": str(inputs["redact"]),
             "TEST_LOG_PATH": str(inputs["root"] / "log-path"),
             "TEST_LAUNCH_COUNT": str(inputs["root"] / "launch-count")},
    )
    try:
        deadline = time.monotonic() + 5
        while not (inputs["root"] / "log-path").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert (inputs["root"] / "log-path").exists()
        child.send_signal(signal.SIGINT)
        stdout, stderr = child.communicate(timeout=5)
        assert child.returncode == 130
        assert stdout == stderr == b""
        assert not Path((inputs["root"] / "log-path").read_text()).exists()
        assert (inputs["root"] / "launch-count").read_text() == "launch\n"
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


def test_unknown_traceback_invalid_encoding_and_oversized_frames_are_suppressed(monkeypatch):
    """Fail closed for unrecognized child text without revealing raw fragments."""
    monkeypatch.setattr(qyrus_private, "MAX_FRAME_BYTES", 64)
    for raw in (b'Traceback: synthetic-secret\n', b'\xffsynthetic-secret',
                b'{"content":"' + b'x' * 80 + b'synthetic-secret"}\n',
                b'{"content":"synthetic-secret"'):
        destination = io.StringIO()
        output = qyrus_private.JsonOutput(destination, qyrus_private.Redactor(["synthetic-secret"]))
        output.feed(raw, final=True)
        assert json.loads(destination.getvalue()) == {"private_output_suppressed": True}
        assert "synthetic-secret" not in destination.getvalue()


def test_argparse_errors_do_not_echo_unknown_values(inputs):
    """Malformed wrapper options cannot print even an unrecognized secret argument."""
    result = invoke(inputs, ["sessions", "list", "--json"],
                    extras=["--unknown", "synthetic-unknown-secret"])
    assert result.returncode == 2
    assert "synthetic-unknown-secret" not in result.stderr
    assert "Invalid private CLI arguments" in result.stderr

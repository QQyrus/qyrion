"""Exercise Windows launch semantics without real credentials or Qyrus calls."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import qyrus_process


@pytest.mark.parametrize("returncode,expected", [(0, 0), (7, 7), (0xC0000005, -1073741819)])
def test_windows_resolves_executable_and_preserves_exit(monkeypatch, returncode, expected):
    """Use resolved argv, inherited stdio and exact status without CRT exec."""
    env = {"PATH": "synthetic-search-path", "QYRION_API_KEY": "synthetic-only-key"}
    executable = r"C:\Users\Test User\bin\qyrion.exe"
    resolved = []
    launched = []

    def resolve(name, *, path):
        """Record executable lookup independently of command arguments."""
        resolved.append((name, path))
        return executable

    def run(argv, **kwargs):
        """Record the process boundary without starting a native executable."""
        launched.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, returncode)

    def forbidden_exec(*args):
        """Fail if the Windows branch enters the unsafe CRT path."""
        pytest.fail("Windows launch must not use execvpe")

    monkeypatch.setattr(qyrus_process, "_WINDOWS", True)
    monkeypatch.setattr(qyrus_process.shutil, "which", resolve)
    monkeypatch.setattr(qyrus_process.subprocess, "run", run)
    monkeypatch.setattr(qyrus_process.os, "execvpe", forbidden_exec)
    command = ["qyrion", "sessions", "list", "--json"]
    assert qyrus_process.launch_command(command, env) == expected
    assert command[0] == "qyrion"
    assert resolved == [("qyrion", "synthetic-search-path")]
    assert launched == [([executable, *command[1:]], {"env": env, "shell": False, "check": False})]


def test_windows_missing_explicit_executable_has_no_fallback(monkeypatch):
    """An invalid override must not silently launch a different PATH command."""
    lookups = []

    def resolve(name, *, path):
        """Record the single explicit executable lookup."""
        lookups.append(name)
        return None

    monkeypatch.setattr(qyrus_process, "_WINDOWS", True)
    monkeypatch.setattr(qyrus_process.shutil, "which", resolve)
    with pytest.raises(FileNotFoundError, match="unavailable"):
        qyrus_process.launch_command(["missing-explicit-qyrion.exe", "--help"], {})
    assert lookups == ["missing-explicit-qyrion.exe"]


def test_posix_keeps_process_replacement(monkeypatch):
    """POSIX still transfers ownership of streams and signals through exec."""
    command = ["qyrion", "sessions", "stream", "fixture-session"]
    env = {"QYRION_API_KEY": "synthetic-only-key"}

    def replace(executable, argv, environment):
        """Check the exec boundary and model its non-returning success."""
        assert (executable, argv, environment) == ("qyrion", command, env)
        raise SystemExit(0)

    monkeypatch.setattr(qyrus_process, "_WINDOWS", False)
    monkeypatch.setattr(qyrus_process.os, "execvpe", replace)
    with pytest.raises(SystemExit) as exited:
        qyrus_process.launch_command(command, env)
    assert exited.value.code == 0


def test_windows_interrupt_is_not_retried(monkeypatch):
    """Translate cancellation to exit 130 without relaunching the command."""
    calls = []

    def interrupt(argv, **kwargs):
        """Model subprocess cleanup followed by the parent's interruption."""
        calls.append(argv)
        raise KeyboardInterrupt

    monkeypatch.setattr(qyrus_process, "_WINDOWS", True)
    monkeypatch.setattr(qyrus_process.shutil, "which", lambda *args, **kwargs: "qyrion.exe")
    monkeypatch.setattr(qyrus_process.subprocess, "run", interrupt)
    assert qyrus_process.launch_command(["qyrion", "capabilities", "--json"], {}) == 130
    assert len(calls) == 1


def test_windows_launch_branch_streams_with_private_environment(tmp_path):
    """Run the Windows branch with real pipes on this host; no Windows claim."""
    credential_file = tmp_path / "private credentials.env"
    credential_file.write_text(
        "X-API-Key=synthetic-only-key\nQYRION_APP_URL=stg.qyrus.com\n"
        "QYRION_TEAM_ID=fixture-team\n"
    )
    credential_file.chmod(0o600)
    child = tmp_path / "command with spaces.py"
    child.write_text(
        "import json, os, sys\n"
        "assert os.environ['QYRION_API_KEY'] == 'synthetic-only-key'\n"
        "assert os.environ['QYRION_TEAM_ID'] == 'fixture-team'\n"
        "assert 'synthetic-only-key' not in sys.argv\n"
        "print(json.dumps({'input': input(), 'argv': sys.argv[1:]}), flush=True)\n"
        "print('child-stderr', file=sys.stderr, flush=True)\n"
        "raise SystemExit(7)\n"
    )
    bootstrap = (
        "import sys; sys.path.insert(0, sys.argv.pop(1)); "
        "import qyrus_process; qyrus_process._WINDOWS = True; "
        "import qyrus_env; raise SystemExit(qyrus_env.main())"
    )
    literal = 'space and "quotes" & $()'
    result = subprocess.run(
        [sys.executable, "-c", bootstrap, str(SCRIPTS), "run", "--env-file",
         str(credential_file), "--", "qyrion", str(child), literal],
        input="hello\n", text=True, capture_output=True, timeout=15,
        env={**os.environ, "QYRION_API_KEY": "stale-key", "QYRION_CLI": sys.executable},
    )
    assert result.returncode == 7
    assert json.loads(result.stdout) == {"input": "hello", "argv": [literal]}
    assert result.stderr == "child-stderr\n"
    assert "synthetic-only-key" not in result.stdout + result.stderr


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_mcp_bootstrap_windows_branch_preserves_stdio(host, tmp_path):
    """Exercise each host's actual bootstrap through the subprocess branch."""
    root = SCRIPTS.parent
    server = json.loads((root / ".mcp.json").read_text())["mcpServers"]["qyrus"]
    env = dict(os.environ, QYRUS_ENV_FILE=str(tmp_path / "not-configured.env"))
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    if host == "claude":
        env["CLAUDE_PLUGIN_ROOT"] = str(root)
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "import qyrus_process; qyrus_process._WINDOWS = True; exec(sys.argv[2])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(SCRIPTS), server["args"][1]],
        cwd=root if host == "codex" else tmp_path,
        env=env, input="", text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 2
    assert not result.stdout
    assert "Cannot read Qyrus credentials" in result.stderr
    assert "Traceback" not in result.stderr

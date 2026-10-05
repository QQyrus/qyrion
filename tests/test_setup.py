"""Offline credential isolation, endpoint derivation, and process-boundary tests."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import qyrus_env


@pytest.fixture
def private_env(tmp_path, monkeypatch):
    """Provide synthetic private credentials and isolate all saved-path state."""
    monkeypatch.setattr(qyrus_env, "config_path", lambda: tmp_path / "config/plugin.json")
    monkeypatch.delenv("QYRUS_ENV_FILE", raising=False)
    path = tmp_path / "private credentials.env"
    path.write_text('# user comment\nX-API-Key="synthetic-only-key"\nQYRION_APP_URL=stg.qyrus.com\n')
    path.chmod(0o600)
    return path


@pytest.mark.parametrize("value,tenant", [
    ("stg.qyrus.com", "stg"), ("https://app.qyrus.com", "app"),
    ("https://qa-2.qyrus.com/", "qa-2"), ("HTTPS://STG.QYRUS.COM", "stg"),
])
def test_endpoint_derivation(value, tenant):
    """Infer the user-specified env-name pattern including app-mcp."""
    assert qyrus_env.application_endpoints(value) == (
        f"https://{tenant}.qyrus.com", f"https://{tenant}-mcp.qyrus.com/mcp"
    )


@pytest.mark.parametrize("url", [
    "http://stg.qyrus.com", "https://evil.example", "qyrus.com",
    "https://stg.qyrus.com@evil.example", "https://stg.qyrus.com/path",
    "https://stg.qyrus.com?key=secret", "https://stg.qyrus.com:443",
    "https://nested.stg.qyrus.com", "https://stg.qyrus.com/#secret",
])
def test_invalid_tenant_never_echoed(url):
    """Reject malformed or non-tenant destinations without reflecting input."""
    with pytest.raises(qyrus_env.SetupError) as error:
        qyrus_env.application_endpoints(url)
    if url != "qyrus.com":
        assert url not in str(error.value)
    assert "secret" not in str(error.value)


def test_maps_one_key_and_removes_stale_overrides(private_env, monkeypatch):
    """The selected file drives all products despite stale inherited settings."""
    monkeypatch.setenv("QYRION_API_KEY", "old-key")
    monkeypatch.setenv("QYRION_RUNBRIDGE_URL", "https://old.example")
    monkeypatch.setenv("QYRION_AUTHORIZATION", "old-token")
    monkeypatch.setenv("QYRION_TEAM_ID", "old-team")
    monkeypatch.setenv("QYRUS_MCP_URL", "https://old.example/mcp")
    with private_env.open("a") as handle:
        handle.write("QYRUS_MCP_URL=https://stale.example/mcp\n")
    env = qyrus_env.load_environment(str(private_env))
    assert env["QYRION_API_KEY"] == env["QYRUS_API_KEY"] == "synthetic-only-key"
    assert env["QYRUS_MCP_URL"] == "https://stg-mcp.qyrus.com/mcp"
    assert env["QYRION_APP_URL"] == "https://stg.qyrus.com"
    assert env["QYRION_RUNBRIDGE_URL"] == "https://stg-gateway.qyrus.com/df-ai-sessions-runbridge-cli/v1"
    assert env["QYRION_TESTHUB_URL"] == "https://stg-gateway.qyrus.com/df-ai-sessions-testhub-cli/v1"
    assert not {"QYRION_AUTHORIZATION", "QYRION_TEAM_ID"} & env.keys()


def test_configure_preserves_secrets_and_is_idempotent(private_env, monkeypatch, capsys):
    """Write only the derived endpoint and remember only the path, without echoes."""
    original = private_env.read_text()
    prepared = []
    monkeypatch.setattr(qyrus_env, "ensure_sdk", lambda: prepared.append(True))
    monkeypatch.setattr(sys, "argv", ["qyrus_env.py", "configure", "--env-file", str(private_env)])
    assert qyrus_env.main() == 0
    assert private_env.read_text() == original + "QYRUS_MCP_URL=https://stg-mcp.qyrus.com/mcp\n"
    assert qyrus_env.main() == 0
    assert private_env.read_text().count("QYRUS_MCP_URL=") == 1
    assert private_env.stat().st_mode & 0o777 == 0o600
    assert json.loads(qyrus_env.config_path().read_text()) == {"env_file": str(private_env)}
    assert "synthetic-only-key" not in str(capsys.readouterr())
    private_env.write_text(private_env.read_text().replace("QYRION_APP_URL=stg", "QYRION_APP_URL=app"))
    assert qyrus_env.main() == 0
    assert "QYRUS_MCP_URL=https://app-mcp.qyrus.com/mcp" in private_env.read_text()
    assert len(prepared) == 3


def test_sdk_install_failure_is_sanitized(monkeypatch):
    """Failed package-index access does not expose the subprocess's private details."""
    def fail(*args, **kwargs):
        """Simulate an installer failure containing a credential-bearing URL."""
        raise OSError("https://user:private-token@index.example")
    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(qyrus_env.SetupError) as error:
        qyrus_env.ensure_sdk()
    assert "private-token" not in str(error.value)
    assert "uv" in str(error.value)


def test_sdk_runner_prepares_package_and_shares_key(private_env):
    """The SDK command supplies the pinned package automatically with the shared key."""
    code = (
        "import os; from importlib.metadata import version; import qyrusai; "
        "assert os.environ['QYRUS_API_KEY']=='synthetic-only-key'; "
        "assert version('qyrusai')=='1.0.9'; print('sdk-ready')"
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "qyrus_env.py"), "sdk", "--env-file", str(private_env),
         "--", "-c", code], text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 0, "SDK runtime did not initialize"
    assert result.stdout == "sdk-ready\n"
    assert "synthetic-only-key" not in result.stderr


def test_path_precedence(private_env, monkeypatch, tmp_path):
    """Explicit selection beats env selection, which beats the saved pointer."""
    qyrus_env.save_selection(private_env)
    assert qyrus_env.resolve_env_file() == private_env
    override = tmp_path / "override.env"
    monkeypatch.setenv("QYRUS_ENV_FILE", str(override))
    assert qyrus_env.resolve_env_file() == override
    assert qyrus_env.resolve_env_file(str(private_env)) == private_env


@pytest.mark.parametrize("content", [
    "X-API-Key=secret\nX-API-Key=duplicate\n", "X-API-Key='secret\n",
    "bad secret line\n", "X-API-Key=<your-xapi-key>\n", "X-API-Key=secret\n",
])
def test_invalid_file_errors_do_not_echo_values(private_env, content):
    """Malformed lines, duplicate keys, placeholders, and missing tenant fail safely."""
    private_env.write_text(content)
    with pytest.raises(qyrus_env.SetupError) as error:
        qyrus_env.load_environment(str(private_env))
    assert "secret" not in str(error.value)
    assert "duplicate\n" not in str(error.value)


def test_shell_expressions_are_literal(private_env, tmp_path):
    """A dotenv file cannot execute commands or interpolate environment secrets."""
    marker = tmp_path / "must-not-exist"
    value = f"$(touch {marker})-${{HOME}}-`whoami`"
    private_env.write_text(f"X-API-Key='{value}'\nQYRION_APP_URL=stg.qyrus.com\n")
    assert qyrus_env.load_environment(str(private_env))["QYRUS_API_KEY"] == value
    assert not marker.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX file mode enforcement")
def test_requires_private_permissions(private_env):
    """World-readable credential files fail before use."""
    private_env.chmod(0o644)
    with pytest.raises(qyrus_env.SetupError, match="chmod 600"):
        qyrus_env.load_environment(str(private_env))


def test_child_receives_key_without_argument_or_output(private_env):
    """A real subprocess sees mapped credentials while public output stays secret-free."""
    code = (
        "import os,sys; "
        "assert os.environ['QYRION_API_KEY']==os.environ['QYRUS_API_KEY']=='synthetic-only-key'; "
        "assert os.environ['QYRUS_MCP_URL']=='https://stg-mcp.qyrus.com/mcp'; "
        "print('child-ok'); sys.exit(7)"
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "qyrus_env.py"), "run", "--env-file", str(private_env),
         "--", sys.executable, "-c", code], text=True, capture_output=True, timeout=10,
    )
    assert result.returncode == 7
    assert result.stdout == "child-ok\n"
    assert "synthetic-only-key" not in result.stderr


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_manifest_bootstrap_resolves_installed_plugin(host, tmp_path):
    """Launch the packaged command from each host path convention with no real key."""
    root = SCRIPTS.parent
    server = json.loads((root / ".mcp.json").read_text())["mcpServers"]["qyrus"]
    env = dict(os.environ, QYRUS_ENV_FILE=str(tmp_path / "not-configured.env"))
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    if host == "claude":
        env["CLAUDE_PLUGIN_ROOT"] = str(root)
    result = subprocess.run(
        [server["command"], *server["args"]],
        cwd=root if host == "codex" else tmp_path,
        env=env, input="", text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 2
    assert not result.stdout
    assert "Cannot read Qyrus credentials" in result.stderr
    assert "Traceback" not in result.stderr

"""Verify Antigravity registration without real credentials or host mutations."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import qyrus_antigravity as adapter


@pytest.fixture
def entry(tmp_path, monkeypatch):
    """Build a command for a simulated installed package whose path has spaces."""
    root = tmp_path / "installed plugin"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts/qyrus_mcp.py").write_text("# fixture bridge\n")
    uv = tmp_path / "uv directory/uv"
    monkeypatch.setattr(adapter.shutil, "which", lambda name: str(uv))
    return adapter.server_entry(root, "uv")


def test_native_manifest_and_skills():
    """Keep the manifest within Google's documented schema and reuse nine skills."""
    root = SCRIPTS.parent
    manifest = json.loads((root / "plugin.json").read_text())
    assert set(manifest) == {"name", "description"}
    assert manifest["name"] == "qyrusai-assure"
    assert len(list((root / "skills").glob("*/SKILL.md"))) == 9


def test_register_preserves_connectors_and_is_idempotent(tmp_path, entry):
    """Merging Qyrus preserves existing secrets/settings and a repeat is byte-stable."""
    path = tmp_path / "mcp_config.json"
    other = {"serverUrl": "https://tracker.example/mcp", "headers": {"Authorization": "synthetic-secret"}}
    path.write_text(json.dumps({"mcpServers": {"tracker": other}, "customSetting": True}))
    assert adapter.register_server(path, entry)
    first = path.read_bytes()
    result = json.loads(first)
    assert result["mcpServers"] == {"tracker": other, "qyrus": entry}
    assert result["customSetting"] is True
    assert not adapter.register_server(path, entry)
    assert path.read_bytes() == first
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600


def test_server_definition_has_absolute_paths_and_no_key(entry):
    """The host receives a native argv vector without secrets or root placeholders."""
    assert Path(entry["command"]).is_absolute()
    assert Path(entry["cwd"]).is_absolute()
    assert Path(entry["args"][-1]).is_absolute()
    assert entry["args"][:3] == ["run", "--quiet", "--script"]
    assert set(entry) == {"command", "args", "cwd"}
    assert "${" not in json.dumps(entry)


def test_conflict_is_non_destructive_and_explicit_replacement_keeps_restrictions(tmp_path, entry):
    """Changing Qyrus needs intent and never re-enables disabled tools or servers."""
    path = tmp_path / "mcp_config.json"
    path.write_text(json.dumps({"mcpServers": {"qyrus": {
        "serverUrl": "https://stg-mcp.qyrus.com/mcp", "headers": {"X-API-Key": "synthetic-secret"},
        "disabled": True, "disabledTools": ["example_write"],
    }}}))
    before = path.read_bytes()
    with pytest.raises(adapter.RegistrationError, match="different qyrus"):
        adapter.register_server(path, entry)
    assert path.read_bytes() == before
    assert adapter.register_server(path, entry, replace_qyrus=True)
    current = json.loads(path.read_bytes())["mcpServers"]["qyrus"]
    assert current == {**entry, "disabled": True, "disabledTools": ["example_write"]}
    assert "synthetic-secret" not in path.read_text()
    assert not adapter.register_server(path, entry)


@pytest.mark.parametrize("data", [b"{secret", b"[]", b'{"mcpServers":[]}', b'\xff', b'{"mcpServers":{},"mcpServers":{}}'])
def test_bad_config_is_preserved_without_echoing_it(tmp_path, entry, data):
    """Malformed and ambiguous JSON is never replaced by a partial configuration."""
    path = tmp_path / "mcp_config.json"
    path.write_bytes(data)
    with pytest.raises(adapter.RegistrationError) as error:
        adapter.register_server(path, entry)
    assert "secret" not in str(error.value)
    assert path.read_bytes() == data


def test_new_nested_config_and_windows_bom_are_supported(tmp_path, entry):
    """First setup creates parent directories and accepts a BOM on subsequent reads."""
    path = tmp_path / "new directory/mcp_config.json"
    assert adapter.register_server(path, entry)
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    assert not adapter.register_server(path, entry)


def test_failed_atomic_replace_leaves_original_and_cleans_temp_file(tmp_path, monkeypatch, entry):
    """A write failure does not truncate connectors or leave a secret-bearing copy."""
    path = tmp_path / "mcp_config.json"
    path.write_text('{"mcpServers":{}}')
    before = path.read_bytes()

    def deny_replace(*args):
        """Simulate an OS denial after the replacement file has been written."""
        raise PermissionError("fixture")

    monkeypatch.setattr(adapter.os, "replace", deny_replace)
    with pytest.raises(PermissionError):
        adapter.register_server(path, entry)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("mcp_config.json.*.tmp"))


def test_concurrent_connector_edit_is_not_lost(tmp_path, monkeypatch, entry):
    """Detect a changed config before replacing it with an outdated snapshot."""
    path = tmp_path / "mcp_config.json"
    path.write_text('{"mcpServers":{}}')
    real_dump = adapter.json.dump
    newer = '{"mcpServers":{"new-tracker":{"serverUrl":"https://example.com/mcp"}}}'

    def edit_while_serializing(*args, **kwargs):
        """Model a second configuration writer during temporary-file creation."""
        path.write_text(newer)
        return real_dump(*args, **kwargs)

    monkeypatch.setattr(adapter.json, "dump", edit_while_serializing)
    with pytest.raises(adapter.RegistrationError, match="changed during setup"):
        adapter.register_server(path, entry)
    assert path.read_text() == newer
    assert not list(tmp_path.glob("mcp_config.json.*.tmp"))


def test_missing_uv_is_actionable(tmp_path, monkeypatch):
    """A missing prerequisite does not create an unusable MCP entry."""
    monkeypatch.setattr(adapter.shutil, "which", lambda name: None)
    with pytest.raises(adapter.RegistrationError, match="uv is unavailable"):
        adapter.server_entry(SCRIPTS.parent, "missing-uv")


def test_registered_command_runs_existing_bridge_from_unrelated_cwd(tmp_path):
    """Smoke-test the real stdio command with absent credentials and no Qyrus call."""
    entry = adapter.server_entry(SCRIPTS.parent, "uv")
    env = {**os.environ, "QYRUS_ENV_FILE": str(tmp_path / "missing-private.env")}
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    result = subprocess.run(
        [entry["command"], *entry["args"]], cwd=tmp_path, env=env,
        input="", capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 2
    assert not result.stdout
    assert "Cannot read Qyrus credentials" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_writes_only_to_explicit_fixture_config(tmp_path):
    """Exercise the shipped command without touching the user's Antigravity profile."""
    path = tmp_path / "profile/mcp_config.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "qyrus_antigravity.py"), "--config", str(path)],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "Registration is not authentication" in result.stdout
    assert not result.stderr
    assert json.loads(path.read_bytes())["mcpServers"]["qyrus"]["cwd"] == str(SCRIPTS.parent)

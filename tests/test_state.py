"""Offline coverage for private, scoped resource references and shared state I/O."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import qyrus_env
import qyrus_state as state


@pytest.fixture
def private_env(tmp_path, monkeypatch):
    """Provide a private synthetic tenant/team without touching the user's profile."""
    monkeypatch.setattr(qyrus_env, "config_path", lambda: tmp_path / "selector.json")
    monkeypatch.delenv("QYRUS_ENV_FILE", raising=False)
    path = tmp_path / "private credentials.env"
    path.write_text("X-API-Key=synthetic-private-key\nQYRION_APP_URL=https://STG.QYRUS.COM/\nQYRION_TEAM_ID=team-1\n")
    path.chmod(0o600)
    return str(path)


def test_records_are_scoped_by_tenant_team_and_exact_target(private_env):
    """A lookup cannot borrow another tenant, team, or target's prior identifiers."""
    record = state.record_resource({"kind": "test", "id": "test-1"}, private_env,
                                   target="https://EXAMPLE.test:443/", verified=True)
    assert record["scope"] == {"qyrus_app_url": "https://stg.qyrus.com", "team_id": "team-1", "target_origin": "https://example.test"}
    assert record["verified_at"] == record["recorded_at"]
    assert state.list_resources(private_env, target="https://example.test") == [record]
    assert state.list_resources(private_env) == []
    assert state.list_resources(private_env, team="team-2", target="https://example.test") == []
    assert state.list_resources(private_env, target="https://other.example.test") == []
    path = Path(private_env)
    path.write_text(path.read_text().replace("STG.QYRUS.COM", "app.qyrus.com"))
    assert state.list_resources(private_env, target="https://example.test") == []


def test_missing_team_is_actionable_and_explicit_team_overrides(private_env):
    """Unset team selection never writes records into an ambiguous global bucket."""
    path = Path(private_env)
    path.write_text(path.read_text().replace("QYRION_TEAM_ID=team-1\n", ""))
    with pytest.raises(state.StateError, match="Select a Qyrus team"):
        state.list_resources(private_env)
    record = state.record_resource({"kind": "suite", "id": "suite-1"}, private_env, team="team-2")
    assert state.list_resources(private_env, team="team-2") == [record]


def test_reference_path_respects_existing_selection(private_env, monkeypatch):
    """The same env selector used by CLI/MCP also locates durable plugin state."""
    monkeypatch.setenv("QYRUS_ENV_FILE", private_env)
    assert state.state_directory() == Path(private_env).parent / "qyrusai-assure"
    assert not state.state_directory().exists()


def test_recording_does_not_assert_success(private_env):
    """Persisting a resource is separate from verification and execution outcome."""
    record = state.record_resource({"kind": "test", "id": "test-1", "status": "created"}, private_env)
    assert record["verified_at"] is None
    assert record["resource"]["outcome"] == "unverified"
    assert "passed" not in json.dumps(record)


def test_api_resource_outcome_is_separate_from_readback(private_env):
    """MCP-created resources support API scope without manufacturing execution success."""
    record = state.record_resource({"kind": "test", "id": "api-test-1", "platform": "api", "status": "completed",
                                   "outcome": "inconclusive"}, private_env, verified=True)
    assert record["resource"]["outcome"] == "inconclusive"
    assert record["verified_at"] is not None
    assert state.list_resources(private_env) == [record]


def test_concurrent_writers_do_not_lose_observations(private_env):
    """Independent per-record files preserve every result of parallel sessions."""
    def write(number):
        """Append one uniquely identified observation from a concurrent caller."""
        return state.record_resource({"kind": "session", "id": f"session-{number}"}, private_env)

    with ThreadPoolExecutor(max_workers=8) as executor:
        records = list(executor.map(write, range(40)))
    loaded = state.list_resources(private_env)
    assert len(loaded) == 40
    assert {record["record_id"] for record in loaded} == {record["record_id"] for record in records}
    assert not list(state.state_directory(private_env).rglob("*.tmp"))


@pytest.mark.parametrize("metadata", [
    {"kind": "test", "id": "test-1", "objective": "Do not save free text"},
    {"kind": "test", "id": "test-1", "password": "secret-value"},
    {"kind": "test", "id": "https://target.test/path?token=secret-value"},
    {"kind": "test", "id": "test-1", "source_issue": "user@example.test"},
    {"kind": "test", "id": "test-1", "status": "passed"},
    {"kind": "test", "id": "test-1", "platform": "secret-value"},
])
def test_rejects_unknown_fields_urls_and_prose_without_echo(private_env, metadata):
    """The registry accepts resource metadata, not arbitrary transcripts or URLs."""
    with pytest.raises(state.StateError) as error:
        state.record_resource(metadata, private_env)
    assert "secret-value" not in str(error.value)
    assert not state.state_directory(private_env).exists()


def test_known_credential_cannot_be_saved_as_an_identifier(private_env):
    """Even ID-shaped known API keys are rejected if accidentally supplied."""
    with pytest.raises(state.StateError, match="known credential") as error:
        state.record_resource({"kind": "test", "id": "synthetic-private-key"}, private_env)
    assert "synthetic-private-key" not in str(error.value)


@pytest.mark.parametrize("origin", [
    "https://user:secret-value@example.test", "https://example.test?key=secret-value",
    "https://example.test/#secret-value", "https://example.test/path", "file:///secret-value",
])
def test_target_scope_cannot_include_secrets_or_paths(private_env, origin):
    """Target scope stores an origin only, never a signed or authenticated URL."""
    with pytest.raises(state.StateError) as error:
        state.record_resource({"kind": "session", "id": "session-1"}, private_env, target=origin)
    assert "secret-value" not in str(error.value)


def test_posix_state_has_private_permissions(private_env):
    """Written state and intermediate state directories remain private on POSIX."""
    state.record_resource({"kind": "suite", "id": "suite-1"}, private_env)
    if os.name == "posix":
        root = state.state_directory(private_env)
        assert root.stat().st_mode & 0o777 == 0o700
        for path in root.rglob("*"):
            assert path.stat().st_mode & 0o777 == (0o700 if path.is_dir() else 0o600)


def test_invalid_stored_data_is_not_echoed(private_env):
    """A damaged or manually edited reference cannot leak arbitrary text on list."""
    state.record_resource({"kind": "test", "id": "test-1"}, private_env)
    path = next(state.state_directory(private_env).rglob("*.json"))
    record = json.loads(path.read_text())
    record["resource"]["password"] = "secret-value"
    path.write_text(json.dumps(record))
    with pytest.raises(state.StateError) as error:
        state.list_resources(private_env)
    assert "secret-value" not in str(error.value)


def test_atomic_failure_preserves_previous_file_and_removes_temporary(tmp_path, monkeypatch):
    """A failed replacement does not truncate an update state or leave partial JSON."""
    path = tmp_path / "private state/updates.json"
    state.atomic_write_json(path, {"before": True})
    before = path.read_bytes()

    def fail_replace(*args):
        """Model a filesystem error at the atomic replacement boundary."""
        raise PermissionError("synthetic failure")

    monkeypatch.setattr(state.os, "replace", fail_replace)
    with pytest.raises(PermissionError):
        state.atomic_write_json(path, {"after": True})
    assert path.read_bytes() == before
    assert list(path.parent.iterdir()) == [path]


def test_state_lock_is_bounded_and_released_after_exception(tmp_path):
    """Competing operations fail within a bound, and exceptions release owned locks."""
    path = tmp_path / "state/.updates.lock"
    with pytest.raises(RuntimeError):
        with state.state_lock(path):
            with pytest.raises(state.StateError, match="busy"):
                with state.state_lock(path, timeout=0.01):
                    pytest.fail("A second writer must not obtain the lock")
            raise RuntimeError("fixture")
    assert not path.exists()
    with state.state_lock(path):
        assert path.is_dir()


def test_state_symlink_is_rejected(private_env, tmp_path):
    """Local state cannot be redirected through a symlink to an unrelated folder."""
    destination = tmp_path / "elsewhere"
    destination.mkdir()
    try:
        state.state_directory(private_env).symlink_to(destination, target_is_directory=True)
    except OSError:
        pytest.skip("This host does not permit symlink creation")
    with pytest.raises(state.StateError, match="symbolic links"):
        state.record_resource({"kind": "test", "id": "test-1"}, private_env)
    assert not list(destination.iterdir())


def test_cli_roundtrip_with_spaces_and_no_credential_echo(private_env, tmp_path):
    """The real argv interface runs from unrelated paths without shell assumptions."""
    command = [sys.executable, str(SCRIPTS / "qyrus_state.py")]
    result = subprocess.run([*command, "record", "--env-file", private_env, "--kind", "test", "--id", "test-1",
                             "--platform", "web", "--project-id", "project-1", "--source-issue", "MON-65", "--verified"],
                            cwd=tmp_path, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0
    record = json.loads(result.stdout)
    listed = subprocess.run([*command, "list", "--env-file", private_env, "--kind", "test"],
                            cwd=tmp_path, text=True, capture_output=True, timeout=10)
    assert listed.returncode == 0
    assert json.loads(listed.stdout) == [record]
    assert "synthetic-private-key" not in result.stdout + result.stderr + listed.stdout + listed.stderr


def test_invalid_cli_arguments_never_echo_values(tmp_path):
    """Accidentally providing a password-like unsupported flag emits a safe hint."""
    result = subprocess.run([sys.executable, str(SCRIPTS / "qyrus_state.py"), "record", "--password", "secret-value"],
                            cwd=tmp_path, text=True, capture_output=True, timeout=10)
    assert result.returncode == 2
    assert "secret-value" not in result.stdout + result.stderr
    assert "Never pass secrets" in result.stderr

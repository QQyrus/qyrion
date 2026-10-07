"""Offline release selection, private state, cadence, and no-install boundaries."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from threading import Event

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import qyrus_updates as updates

NOW = datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc)


def release(version="0.3.5-beta", published="2026-10-06T09:00:00Z", draft=False):
    """Construct synthetic public metadata with all supported binary assets."""
    tag = f"qyrion/v{version}"
    assets = []
    for target in ("windows-x64.exe", "macos-arm64.tar.gz", "linux-x64.tar.gz"):
        name = f"qyrion-{version}-{target}"
        assets.append({"name": name, "browser_download_url": f"https://github.com/QQyrus/qyrion/releases/download/{tag}/{name}"})
    return {"tag_name": tag, "draft": draft, "published_at": published,
            "prerelease": "-" in version, "assets": assets}


@pytest.fixture
def update_env(tmp_path, monkeypatch):
    """Select a nonexistent credential path, proving checks need no key contents."""
    path = tmp_path / "private" / "credentials.env"
    monkeypatch.setattr(updates, "platform_target", lambda: "windows-x64.exe")
    monkeypatch.setattr(updates, "newest_release", lambda target: updates.safe_release(release(), target))
    monkeypatch.delenv("QYRION_CLI", raising=False)
    return str(path)


@pytest.mark.parametrize("old,new", [
    ("0.3.4", "0.3.5-beta"), ("0.3.5-beta", "0.3.5"),
    ("0.3.5-beta.2", "0.3.5-beta.10"), ("0.3.5a1", "0.3.5b0"),
    ("0.3.5-beta", "0.3.5-rc.1"), ("0.3.5", "1.0.0"),
])
def test_version_comparison(old, new):
    """Release ordering handles numeric versions and prerelease increments."""
    assert updates.version_key(old) < updates.version_key(new)


def test_python_beta_matches_release_tag():
    """Package-normalized versions do not trigger repeated same-release offers."""
    assert updates.version_key("qyrion/v0.3.5-beta") == updates.version_key("0.3.5b0")


@pytest.mark.parametrize("system,machine,target", [
    ("Windows", "AMD64", "windows-x64.exe"), ("Linux", "x86_64", "linux-x64.tar.gz"),
    ("Darwin", "arm64", "macos-arm64.tar.gz"), ("Darwin", "x86_64", None),
    ("Windows", "ARM64", None),
])
def test_published_platforms(system, machine, target):
    """Unsupported architectures do not silently get an incompatible binary."""
    assert updates.platform_target(system, machine) == target


def test_newest_beta_selected_across_pages(monkeypatch):
    """Use published time across pagination, never latest stable or API order."""
    seen = []
    next_page = updates.RELEASES_URL + "&page=2"
    def page(url, timeout):
        """Return a stable page followed by a newer beta with unrelated entries."""
        seen.append(url)
        assert 0 < timeout <= 5
        if len(seen) == 1:
            return [release("0.3.4", "2026-10-01T00:00:00Z")], f'<{next_page}>; rel="next"'
        return [release(), release("0.4.0", "2026-10-07T00:00:00Z", draft=True),
                {"tag_name": "other/v9", "draft": False, "published_at": "2026-10-08T00:00:00Z"}], ""
    monkeypatch.setattr(updates, "get_page", page)
    found = updates.newest_release("windows-x64.exe")
    assert seen == [updates.RELEASES_URL, next_page]
    assert found["version"] == "0.3.5-beta"
    assert found["prerelease"] is True
    assert found["asset"]["name"] == "qyrion-0.3.5-beta-windows-x64.exe"


@pytest.mark.parametrize("url", [
    "https://evil.example/releases?per_page=100", "https://api.github.com/user?per_page=100",
    "https://api.github.com/repos/QQyrus/qyrion/releases?per_page=100&token=secret",
    "https://api.github.com/repos/QQyrus/qyrion/releases?per_page=100&page=2#secret",
])
def test_pagination_cannot_change_origin_or_send_secrets(url):
    """Only the public release-list endpoint and pagination parameters are allowed."""
    with pytest.raises(updates.UpdateError):
        updates.validate_page_url(url)


def test_incomplete_pagination_not_reported_as_current(monkeypatch):
    """Reaching the page cap fails instead of advertising a partial release set."""
    def page(url, timeout):
        """Supply a next page beyond the bounded traversal budget."""
        return [release()], f'<{updates.RELEASES_URL}&page=2>; rel="next"'
    monkeypatch.setattr(updates, "get_page", page)
    monkeypatch.setattr(updates, "MAX_PAGES", 1)
    with pytest.raises(updates.UpdateError, match="pagination limit"):
        updates.newest_release()


def test_official_assets_only():
    """An exact filename cannot make an off-site or signed URL trusted."""
    item = release()
    item["assets"][0]["browser_download_url"] = "https://evil.example/qyrion.exe?token=secret"
    found = updates.safe_release(item, "windows-x64.exe")
    assert found["asset"] is None
    assert "secret" not in json.dumps(found)


def test_four_hour_cadence_timestamps_and_no_install(update_env, monkeypatch):
    """Checks are cached for four hours and cannot claim an installation happened."""
    calls = []
    def fetch(target):
        """Count only synthetic release-list reads."""
        calls.append(target)
        return updates.safe_release(release(), target)
    def forbidden(*args, **kwargs):
        """Reject any attempted executable launch when a version hint was supplied."""
        raise AssertionError("No install or CLI subprocess should run")
    monkeypatch.setattr(updates, "newest_release", fetch)
    monkeypatch.setattr(updates.subprocess, "run", forbidden)
    first = updates.check_updates(update_env, "0.3.4", install_kind="binary", now=NOW)
    cached = updates.check_updates(update_env, "0.3.4", now=NOW + timedelta(hours=3, minutes=59))
    later = updates.check_updates(update_env, "0.3.4", now=NOW + timedelta(hours=4))
    assert len(calls) == 2
    assert first["notify"] and first["requires_user_acceptance"]
    assert not first["preserve_installation"]
    assert not first["cached"] and cached["cached"] and not later["cached"]
    assert first["last_updated_at"] is None
    assert first["last_checked_at"] == first["last_successful_check_at"]
    path = Path(update_env).parent / "qyrusai-assure" / "updates.json"
    assert path.is_file() and not Path(update_env).exists()
    assert "last_updated_at" not in json.loads(path.read_text())


def test_failed_check_preserves_success_and_is_throttled(update_env, monkeypatch):
    """Network errors do not become up-to-date claims or repeatedly block tasks."""
    first = updates.check_updates(update_env, "0.3.4", now=NOW)
    def fail(target):
        """Raise a synthetic sensitive network message that must not be emitted."""
        raise OSError("private upstream URL token=secret")
    monkeypatch.setattr(updates, "newest_release", fail)
    failed = updates.check_updates(update_env, "0.3.4", now=NOW + timedelta(hours=4))
    cached = updates.check_updates(update_env, "0.3.4", now=NOW + timedelta(hours=5))
    assert failed["status"] == "unavailable" and not failed["notify"]
    assert failed["last_successful_check_at"] == first["last_successful_check_at"]
    assert cached["cached"] and not cached["notify"]
    assert "secret" not in json.dumps(failed)


def test_concurrent_check_does_not_duplicate_network_request(update_env, monkeypatch):
    """An overlapping worker yields while the owner performs its bounded check."""
    started, finish = Event(), Event()
    calls = []
    def fetch(target):
        """Hold the first synthetic request while a second worker tries the lock."""
        calls.append(target)
        started.set()
        assert finish.wait(5)
        return updates.safe_release(release(), target)
    monkeypatch.setattr(updates, "newest_release", fetch)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(updates.check_updates, update_env, "0.3.4", now=NOW)
        try:
            assert started.wait(2)
            with pytest.raises(updates.StateError):
                updates.check_updates(update_env, "0.3.4", now=NOW)
        finally:
            finish.set()
        assert pending.result(timeout=2)["status"] == "ok"
    assert len(calls) == 1
    assert updates.check_updates(update_env, "0.3.4", now=NOW)["cached"]


@pytest.mark.parametrize("action", ["offered", "decline"])
def test_offer_bookkeeping_suppresses_repeat_but_new_version_notifies(update_env, monkeypatch, action):
    """One known release is offered once; a distinct future version can notify."""
    updates.check_updates(update_env, "0.3.4", now=NOW)
    updates.record_action(action, "0.3.5-beta", update_env, now=NOW)
    result = updates.check_updates(update_env, "0.3.4", now=NOW + timedelta(hours=1))
    assert result["update_available"] and not result["notify"]
    monkeypatch.setattr(updates, "newest_release", lambda target: updates.safe_release(release("0.3.6-beta"), target))
    assert updates.check_updates(update_env, "0.3.4", now=NOW + timedelta(hours=4))["notify"]


@pytest.mark.parametrize("kind", ["unknown", "source", "editable", "pinned"])
def test_source_and_pinned_installs_are_preserved(update_env, kind):
    """Release visibility never implies permission to replace source or pinned tools."""
    result = updates.check_updates(update_env, "0.2.0", install_kind=kind, now=NOW)
    assert result["preserve_installation"]
    assert result["requires_user_acceptance"]


def test_explicit_override_is_preserved_even_for_binary(update_env, monkeypatch):
    """An explicit executable remains protected despite a binary-source hint."""
    monkeypatch.setenv("QYRION_CLI", "/chosen/path/qyrion")
    result = updates.check_updates(update_env, "0.2.0", install_kind="binary", now=NOW)
    assert result["preserve_installation"]


def test_record_installed_verifies_actual_version_and_latest(update_env, monkeypatch):
    """Only matching executable output plus the checked release permits a timestamp."""
    updates.check_updates(update_env, "0.3.4", now=NOW)
    monkeypatch.setattr(updates, "installed_version", lambda cli: "0.3.4")
    with pytest.raises(updates.UpdateError, match="does not match"):
        updates.record_action("record-installed", "0.3.5-beta", update_env, now=NOW)
    monkeypatch.setattr(updates, "installed_version", lambda cli: "0.3.5b0")
    recorded = updates.record_action("record-installed", "0.3.5-beta", update_env, now=NOW)
    assert recorded["installation_verified"] and not recorded["installed"]
    checked = updates.check_updates(update_env, "0.3.5b0", now=NOW + timedelta(minutes=1))
    assert checked["last_updated_at"] == updates.timestamp(NOW)
    assert not checked["update_available"]
    with pytest.raises(updates.UpdateError):
        updates.record_action("offered", "9.9.9", update_env)


def test_offered_release_survives_newer_cache_for_install_and_decline(update_env, monkeypatch):
    """A cache refresh cannot change the release the user was offered and accepted."""
    first = updates.check_updates(update_env, "0.3.4", now=NOW)
    updates.record_action("offered", "0.3.5-beta", update_env, now=NOW)
    monkeypatch.setattr(updates, "newest_release", lambda target: updates.safe_release(release("0.3.6-beta"), target))
    refreshed = updates.check_updates(update_env, "0.3.4", now=NOW + timedelta(hours=4))
    assert refreshed["latest"]["version"] == "0.3.6-beta"
    assert refreshed["offered_release"] == first["latest"]
    updates.record_action("decline", "0.3.5-beta", update_env)
    monkeypatch.setattr(updates, "installed_version", lambda cli: "0.3.5b0")
    recorded = updates.record_action("record-installed", "0.3.5-beta", update_env, now=NOW + timedelta(hours=5))
    assert recorded["installation_verified"]
    result = updates.check_updates(update_env, "0.3.5b0", now=NOW + timedelta(hours=5))
    assert result["last_updated_at"] == updates.timestamp(NOW + timedelta(hours=5))
    assert result["latest"]["version"] == "0.3.6-beta"


def test_cli_version_handshake_and_sanitized_failure(monkeypatch):
    """Use the real static version command and suppress captured error contents."""
    calls = []
    def run(command, **kwargs):
        """Return a synthetic version envelope from a known executable path."""
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, '{"cli_version":"0.3.5b0"}')
    monkeypatch.setattr(updates.subprocess, "run", run)
    assert updates.installed_version("/path/qyrion") == "0.3.5b0"
    assert calls == [["/path/qyrion", "version", "--json"]]
    def fail(command, **kwargs):
        """Represent a missing executable with a private error detail."""
        raise OSError("secret-token")
    monkeypatch.setattr(updates.subprocess, "run", fail)
    with pytest.raises(updates.UpdateError) as error:
        updates.installed_version()
    assert "secret" not in str(error.value)


def test_public_request_has_no_auth_headers(monkeypatch):
    """No inherited Qyrus key is used in the public GitHub release request."""
    monkeypatch.setenv("QYRUS_API_KEY", "synthetic-secret")
    requests = []
    class Response:
        """Provide a tiny context-managed fake HTTP response."""
        headers = {}
        def __enter__(self):
            """Expose the response for a with block."""
            return self
        def __exit__(self, *args):
            """Complete the fake request without suppressing exceptions."""
        def read(self, limit):
            """Return a public release-list payload."""
            return b"[]"
    def fetch(request, timeout):
        """Capture only fixed public HTTP request metadata."""
        requests.append(request)
        return Response()
    monkeypatch.setattr(updates, "urlopen", fetch)
    assert updates.get_page(updates.RELEASES_URL, 5) == ([], "")
    assert set(name.lower() for name in requests[0].headers) == {"accept", "user-agent"}
    assert "secret" not in repr(requests[0].headers)


def test_invalid_state_never_echoed_or_overwritten(update_env, capsys, monkeypatch):
    """Unknown/secret-bearing metadata causes a quiet safe failure and is preserved."""
    directory = updates.private_directory(updates.state_directory(update_env))
    path = directory / "updates.json"
    updates.atomic_write_json(path, {"schema_version": 1, "password": "synthetic-secret"})
    before = path.read_bytes()
    monkeypatch.setattr(sys, "argv", ["qyrus_updates.py", "check", "--env-file", update_env, "--current-version", "0.3.4"])
    assert updates.main() == 0
    payload = capsys.readouterr().out
    assert "synthetic-secret" not in payload and '"status": "unavailable"' in payload
    assert path.read_bytes() == before

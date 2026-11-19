"""Check public Qyrion releases opportunistically; never download or install.

Example:
    python3 qyrus_updates.py check --env-file ~/.config/qyrus/credentials.env
    python3 qyrus_updates.py offered --version 0.3.5-beta
    python3 qyrus_updates.py record-installed --version 0.3.5-beta --cli /path/qyrion
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from urllib.parse import parse_qs, unquote, urlsplit
from urllib.request import Request, urlopen

from qyrus_env import SetupError
from qyrus_state import StateError, atomic_write_json, private_directory, state_directory, state_lock

RELEASES_URL = "https://api.github.com/repos/QQyrus/qyrion/releases?per_page=100"
INTERVAL_SECONDS = 4 * 60 * 60
MAX_PAGES = 10
MAX_PAGE_BYTES = 2 * 1024 * 1024
INSTALL_KINDS = ("unknown", "binary", "source", "editable", "pinned")
STATE_FIELDS = {
    "schema_version", "last_checked_at", "last_successful_check_at", "last_updated_at",
    "installed_version", "latest", "offered_release", "offered_version", "declined_version", "check_status",
}


class UpdateError(ValueError):
    """Describe update metadata failure without exposing response or process text."""


def version_key(value: str) -> tuple:
    """Compare release SemVer and Python-normalized alpha/beta/rc versions.

    Example: ``0.3.4-beta`` and package metadata ``0.3.4b0`` compare equally.
    """
    if not isinstance(value, str) or len(value) > 100:
        raise UpdateError("Invalid Qyrion version.")
    match = re.fullmatch(r"(?:qyrion/)?v?(\d+)\.(\d+)\.(\d+)(?:(?:-([A-Za-z0-9.]+))|((?:a|b|rc)\d+))?(?:\+[A-Za-z0-9.]+)?", value)
    if not match:
        raise UpdateError("Invalid Qyrion version.")
    major, minor, patch, suffix, python_suffix = match.groups()
    suffix = suffix or python_suffix
    if not suffix:
        return (int(major), int(minor), int(patch), ((2, ""),))
    known = re.fullmatch(r"(alpha|beta|rc|a|b)(?:\.?([0-9]+))?", suffix)
    if known:
        stage = {"a": "alpha", "b": "beta"}.get(known[1], known[1])
        suffix = f"{stage}.{int(known[2] or 0)}"
    parts = tuple((0, int(part)) if part.isdigit() else (1, part) for part in suffix.split("."))
    return (int(major), int(minor), int(patch), parts)


def timestamp(value: datetime) -> str:
    """Serialize an aware timestamp as UTC seconds for portable private state."""
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    """Parse only an aware ISO timestamp; never echo malformed state values."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError):
        raise UpdateError("Invalid update timestamp.") from None


def platform_target(system: str | None = None, machine: str | None = None) -> str | None:
    """Return the published user-local binary target for the host, if supported."""
    system, machine = system or platform.system(), (machine or platform.machine()).lower()
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64.tar.gz"
    if system == "Linux" and machine in {"amd64", "x86_64", "x64"}:
        return "linux-x64.tar.gz"
    if system == "Windows" and machine in {"amd64", "x86_64", "x64"}:
        return "windows-x64.exe"
    return None


def safe_release(raw: dict, target: str | None) -> dict | None:
    """Retain only validated public release metadata and the exact platform asset."""
    if not isinstance(raw, dict) or raw.get("draft") is not False:
        return None
    tag = raw.get("tag_name", "")
    if not isinstance(tag, str) or not tag.startswith("qyrion/v"):
        return None
    version = tag[len("qyrion/v"):]
    try:
        version_key(version)
        published = timestamp(parse_timestamp(raw.get("published_at")))
    except UpdateError:
        return None
    release = {"version": version, "published_at": published,
               "prerelease": raw.get("prerelease") is True,
               "url": f"https://github.com/QQyrus/qyrion/releases/tag/{tag}", "asset": None}
    name = f"qyrion-{version}-{target}" if target else None
    for asset in raw.get("assets", []) if isinstance(raw.get("assets"), list) else []:
        if not isinstance(asset, dict) or asset.get("name") != name or name is None:
            continue
        url = asset.get("browser_download_url")
        if not isinstance(url, str):
            continue
        parts = urlsplit(url)
        if (parts.scheme == "https" and parts.netloc == "github.com" and not parts.query
                and not parts.fragment and unquote(parts.path) == f"/QQyrus/qyrion/releases/download/{tag}/{name}"):
            release["asset"] = {"name": name, "url": url}
            break
    return release


def validate_page_url(url: str) -> None:
    """Restrict release pagination to the same public GitHub API endpoint."""
    parts = urlsplit(url)
    query = parse_qs(parts.query, strict_parsing=True)
    if (parts.scheme != "https" or parts.netloc != "api.github.com" or parts.fragment
            or parts.path != "/repos/QQyrus/qyrion/releases"
            or set(query) - {"page", "per_page"}
            or query.get("per_page") != ["100"]
            or ("page" in query and (len(query["page"]) != 1 or not query["page"][0].isdigit()))):
        raise UpdateError("Invalid release pagination.")


def get_page(url: str, timeout: float) -> tuple[list, str]:
    """Fetch one public release page with fixed headers and no Qyrus credentials."""
    validate_page_url(url)
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "qyrusai-assure-update-check"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_PAGE_BYTES + 1)
        if len(payload) > MAX_PAGE_BYTES:
            raise UpdateError("Release response exceeded the safe size limit.")
        releases = json.loads(payload)
        if not isinstance(releases, list):
            raise UpdateError("Unexpected release response.")
        return releases, response.headers.get("Link", "")


def newest_release(target: str | None = None) -> dict:
    """Select the newest published release including betas across bounded pages.

    Pagination failure fails the check rather than presenting a partial list as
    current. Requests have a 30-second total budget and at most ten pages.
    """
    url, seen, releases = RELEASES_URL, set(), []
    deadline = time.monotonic() + 30
    for _ in range(MAX_PAGES):
        if url in seen or time.monotonic() >= deadline:
            raise UpdateError("Release lookup could not complete within its limits.")
        seen.add(url)
        entries, link = get_page(url, min(5.0, max(0.1, deadline - time.monotonic())))
        releases.extend(release for item in entries if (release := safe_release(item, target)))
        next_links = re.findall(r'<([^>]+)>;\s*rel="next"', link)
        if not next_links:
            if not releases:
                raise UpdateError("No published Qyrion release was found.")
            return max(releases, key=lambda release: parse_timestamp(release["published_at"]))
        if len(next_links) != 1:
            raise UpdateError("Invalid release pagination.")
        url = next_links[0]
        validate_page_url(url)
    raise UpdateError("Release lookup exceeded its pagination limit.")


def installed_version(cli: str | None = None) -> str:
    """Read the chosen executable's static version without loading credentials."""
    command = cli or os.environ.get("QYRION_CLI") or "qyrion"
    try:
        result = subprocess.run([command, "version", "--json"], capture_output=True, text=True, timeout=10)
        value = json.loads(result.stdout)["cli_version"] if result.returncode == 0 else None
        version_key(value)
        return value
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        raise UpdateError("Could not verify the installed Qyrion version.") from None


def read_state(path: Path) -> dict:
    """Load only known update fields from a private regular JSON state file."""
    if path.is_symlink():
        raise UpdateError("Update state cannot be a symbolic link.")
    if not path.exists():
        return {"schema_version": 1}
    try:
        if not path.is_file() or path.stat().st_size > 16384:
            raise ValueError
        if os.name == "posix" and path.stat().st_mode & 0o077:
            raise ValueError
        state = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or set(state) - STATE_FIELDS or state.get("schema_version") != 1:
            raise ValueError
        for field in ("last_checked_at", "last_successful_check_at", "last_updated_at"):
            if field in state:
                parse_timestamp(state[field])
        for field in ("installed_version", "offered_version", "declined_version"):
            if field in state:
                version_key(state[field])
        if state.get("check_status") not in (None, "success", "unavailable", "checking"):
            raise ValueError
        for field in ("latest", "offered_release"):
            if field not in state:
                continue
            latest = state[field]
            if not isinstance(latest, dict) or set(latest) != {"version", "published_at", "prerelease", "url", "asset"}:
                raise ValueError
            candidate = safe_release({"draft": False, "tag_name": f"qyrion/v{latest['version']}",
                                      "published_at": latest["published_at"], "prerelease": latest["prerelease"],
                                      "assets": []}, None)
            if candidate is None or latest["url"] != candidate["url"] or type(latest["prerelease"]) is not bool:
                raise ValueError
            if latest["asset"] is not None:
                asset = latest["asset"]
                if not isinstance(asset, dict) or set(asset) != {"name", "url"}:
                    raise ValueError
                if not isinstance(asset["name"], str):
                    raise ValueError
                targets = ("macos-arm64.tar.gz", "linux-x64.tar.gz", "windows-x64.exe")
                raw = {"draft": False, "tag_name": f"qyrion/v{latest['version']}",
                       "published_at": latest["published_at"], "prerelease": latest["prerelease"],
                       "assets": [{"name": asset["name"], "browser_download_url": asset["url"]}]}
                if not any(safe_release(raw, target)["asset"] == asset for target in targets):
                    raise ValueError
        return state
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        raise UpdateError("Invalid or non-private Qyrion update state; inspect updates.json locally.") from None


def result_payload(state: dict, current: str | None, kind: str, cached: bool, override: bool) -> dict:
    """Describe verified availability without implying approval or installing anything."""
    latest = state.get("latest")
    available = bool(current and latest and version_key(latest["version"]) > version_key(current))
    fresh = state.get("check_status") == "success"
    suppressed = bool(latest and any(version_key(state[field]) == version_key(latest["version"])
                                      for field in ("offered_version", "declined_version") if field in state))
    return {"status": "ok" if fresh else "unavailable", "cached": cached,
            "installed_version": current, "latest": latest, "update_available": available if fresh else False,
            "offered_release": state.get("offered_release"),
            "notify": bool(fresh and available and not suppressed), "installation_kind": kind,
            "preserve_installation": kind != "binary" or override, "requires_user_acceptance": True,
            "last_checked_at": state.get("last_checked_at"),
            "last_successful_check_at": state.get("last_successful_check_at"),
            "last_updated_at": state.get("last_updated_at"), "check_interval_hours": 4}


def check_updates(explicit: str | None = None, current_version: str | None = None,
                  cli: str | None = None, install_kind: str = "unknown", force: bool = False,
                  now: datetime | None = None) -> dict:
    """Check at most once per four hours, serializing callers with a private lock.

    GitHub failures are cached as unavailable, never treated as no update. The
    env path selects storage only; its credential contents are never opened.
    """
    if install_kind not in INSTALL_KINDS:
        raise UpdateError("Invalid installation kind.")
    if current_version is not None:
        version_key(current_version)
    else:
        try:
            current_version = installed_version(cli)
        except UpdateError:
            current_version = None
    moment = now or datetime.now(timezone.utc)
    directory = private_directory(state_directory(explicit))
    with state_lock(directory / ".updates.lock", timeout=1):
        path = directory / "updates.json"
        state = read_state(path)
        previous = state.get("last_checked_at")
        elapsed = (moment - parse_timestamp(previous)).total_seconds() if previous else INTERVAL_SECONDS
        cached = not force and 0 <= elapsed < INTERVAL_SECONDS
        if not cached:
            state.update(last_checked_at=timestamp(moment), check_status="checking")
            atomic_write_json(path, state)
            try:
                state["latest"] = newest_release(platform_target())
                state.update(check_status="success", last_successful_check_at=timestamp(moment))
            except (OSError, ValueError, TypeError):
                state["check_status"] = "unavailable"
        if current_version:
            state["installed_version"] = current_version
        atomic_write_json(path, state)
        return result_payload(state, current_version, install_kind, cached, bool(cli or os.environ.get("QYRION_CLI")))


def record_action(action: str, version: str, explicit: str | None = None,
                  cli: str | None = None, now: datetime | None = None) -> dict:
    """Record a displayed/declined offer or an actually verified installed release.

    ``record-installed`` checks the executable; a requested version alone is
    never evidence of a completed update. None of these actions install files.
    """
    version_key(version)
    if action not in {"offered", "decline", "record-installed"}:
        raise UpdateError("Invalid update action.")
    verified = installed_version(cli) if action == "record-installed" else None
    if verified and version_key(verified) != version_key(version):
        raise UpdateError("Installed Qyrion does not match the expected update version.")
    directory = private_directory(state_directory(explicit))
    with state_lock(directory / ".updates.lock", timeout=1):
        path = directory / "updates.json"
        state = read_state(path)
        latest = state.get("latest")
        offered = state.get("offered_release")
        matches_latest = bool(latest and version_key(latest["version"]) == version_key(version))
        matches_offer = bool(offered and version_key(offered["version"]) == version_key(version))
        if not matches_latest and not (action != "offered" and matches_offer):
            raise UpdateError("The requested version does not match a checked or offered public release.")
        if action == "record-installed":
            state.update(installed_version=verified, last_updated_at=timestamp(now or datetime.now(timezone.utc)))
        else:
            state[f"{'offered' if action == 'offered' else 'declined'}_version"] = version
            if action == "offered":
                state["offered_release"] = dict(latest)
        atomic_write_json(path, state)
    return {"recorded": action, "version": version, "installed": False,
            "installation_verified": action == "record-installed"}


def main() -> int:
    """Expose quiet JSON checks and explicit offer bookkeeping without an installer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "offered", "decline", "record-installed"))
    parser.add_argument("--env-file")
    parser.add_argument("--cli")
    parser.add_argument("--version")
    parser.add_argument("--current-version")
    parser.add_argument("--install-kind", choices=INSTALL_KINDS, default="unknown")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "check":
            payload = check_updates(args.env_file, args.current_version, args.cli, args.install_kind, args.force)
        elif not args.version:
            raise UpdateError("This action requires --version from the release check.")
        else:
            payload = record_action(args.action, args.version, args.env_file, args.cli)
        print(json.dumps(payload))
        return 0
    except (UpdateError, StateError, SetupError, OSError):
        print(json.dumps({"status": "unavailable", "notify": False,
                          "message": "Update check or state is unavailable; continue the task and inspect setup locally."}))
        return 0 if args.action == "check" else 2


if __name__ == "__main__":
    raise SystemExit(main())

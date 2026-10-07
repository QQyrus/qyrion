"""Keep private, scoped Qyrus resource references beside the selected credentials.

This is an index of identifiers, not an execution transcript or proof that a
resource still exists. Revalidate references through Qyrus before reusing them.

Example:
    python3 qyrus_state.py record --kind test --id test-123 --platform web \
        --source-issue MON-65 --target-origin https://example.test --verified
    python3 qyrus_state.py list --target-origin https://example.test
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
from urllib.parse import urlsplit
import uuid

from qyrus_env import SetupError, application_endpoints, read_values, resolve_env_file

KINDS = ("test", "suite", "project", "session", "execution", "artifact")
STATUSES = ("created", "running", "completed", "failed", "blocked", "cancelled", "archived", "unknown")
OUTCOMES = ("unverified", "passed", "failed", "inconclusive", "blocked", "running", "cancelled")
IDENTIFIERS = ("id", "source_issue", "project_id", "suite_id", "test_id", "session_id", "execution_id")
FIELDS = {*IDENTIFIERS, "kind", "platform", "status", "outcome"}


class StateError(ValueError):
    """Describe a local-state failure without reflecting private values."""


class PrivateArgumentParser(argparse.ArgumentParser):
    """Avoid echoing accidental secret arguments in CLI validation errors."""

    def error(self, message: str) -> None:
        """Replace argparse's value-bearing error with a safe usage hint."""
        self.exit(2, "Invalid arguments; see --help. Never pass secrets to this helper.\n")


def state_directory(explicit: str | None = None) -> Path:
    """Return the private-state location beside the resolved credentials file."""
    return resolve_env_file(explicit).parent / "qyrusai-assure"


def private_directory(path: Path) -> Path:
    """Create a managed directory, refusing symlinks and securing POSIX access.

    Windows inherits the user's directory ACL; POSIX directories use mode 0700.
    Callers must only pass plugin-managed directories, not arbitrary user homes.
    """
    if path.is_symlink():
        raise StateError("Qyrus state directories must not be symbolic links.")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise StateError("Qyrus state requires a directory.")
    if os.name == "posix":
        if info.st_uid != os.getuid():
            raise StateError("Qyrus state must be owned by the current user.")
        path.chmod(0o700)
    return path


def atomic_write_json(path: Path, payload: dict) -> None:
    """Atomically write private JSON without truncating an existing state file.

    Concurrent read-modify-write callers must hold ``state_lock`` themselves.
    """
    private_directory(path.parent)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise StateError("Qyrus state files must be regular files.")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".state-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def state_lock(path: Path, timeout: float = 5.0):
    """Hold a bounded, cross-platform lock directory until the context exits.

    Example:
        with state_lock(state_directory() / ".updates.lock", timeout=1):
            atomic_write_json(state_directory() / "updates.json", metadata)

    An interrupted process can leave a lock directory. Never steal it by age:
    verify that no checker is running before manually removing a stale lock.
    """
    private_directory(path.parent)
    deadline = time.monotonic() + timeout
    while True:
        try:
            path.mkdir(mode=0o700)
            break
        except FileExistsError:
            if path.is_symlink() or not path.is_dir():
                raise StateError("The Qyrus state lock is invalid.") from None
            if time.monotonic() >= deadline:
                raise StateError("Qyrus state is busy; retry after the other operation finishes.") from None
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    try:
        yield
    finally:
        path.rmdir()


def identifier(value: object) -> str:
    """Accept bounded resource identifiers while rejecting URL and prose syntax.

    Syntax is only an accidental-data guard: arbitrary secrets can resemble IDs.
    Callers must supply identifiers from Qyrus responses, not untrusted prose.
    """
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", value):
        raise StateError("State accepts resource identifiers only; do not store credentials, URLs, or prose.")
    return value


def target_origin(value: str | None) -> str | None:
    """Normalize an optional HTTP(S) origin, rejecting paths and secret-bearing URLs."""
    if value is None:
        return None
    try:
        parts = urlsplit(value)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username or parts.password or parts.query or parts.fragment
                or parts.path not in {"", "/"} or any(c.isspace() for c in value)):
            raise ValueError
        host = parts.hostname.encode("idna").decode("ascii").lower()
        if ":" in host:
            host = f"[{host}]"
        port = parts.port
        suffix = f":{port}" if port and port != {"http": 80, "https": 443}[parts.scheme] else ""
        return f"{parts.scheme}://{host}{suffix}"
    except (ValueError, UnicodeError):
        raise StateError("Target scope must be an HTTP(S) origin without credentials, path, query, or fragment.") from None


def scope_for(explicit: str | None = None, team: str | None = None,
              target: str | None = None) -> tuple[dict, tuple[str, ...]]:
    """Load only the selected tenant/team scope and known secrets for rejection.

    The API key stays in memory and is never part of the returned scope.
    """
    values = read_values(resolve_env_file(explicit))
    app, _ = application_endpoints(values.get("QYRION_APP_URL", ""))
    selected_team = team or values.get("QYRION_TEAM_ID")
    if not selected_team:
        raise StateError("Select a Qyrus team before storing or looking up resource references.")
    scope = {"qyrus_app_url": app, "team_id": identifier(selected_team), "target_origin": target_origin(target)}
    secrets = tuple(value for key, value in values.items() if value and
                    re.search(r"key|token|password|authorization|secret", key, re.IGNORECASE))
    return scope, secrets


def validate_metadata(metadata: dict) -> dict:
    """Validate an allowlisted resource record; unknown fields are never persisted."""
    if not isinstance(metadata, dict) or not set(metadata) <= FIELDS or not {"kind", "id"} <= set(metadata):
        raise StateError("State records require kind and id and accept only documented metadata fields.")
    if not isinstance(metadata["kind"], str) or metadata["kind"] not in KINDS:
        raise StateError("Unsupported Qyrus resource kind.")
    for field in IDENTIFIERS:
        if field in metadata:
            identifier(metadata[field])
    if "platform" in metadata and (not isinstance(metadata["platform"], str) or metadata["platform"] not in {"web", "mobile", "api"}):
        raise StateError("State platform must be web, mobile, or api.")
    if "status" in metadata and (not isinstance(metadata["status"], str) or metadata["status"] not in STATUSES):
        raise StateError("Unsupported observed resource status.")
    if "outcome" in metadata and (not isinstance(metadata["outcome"], str) or metadata["outcome"] not in OUTCOMES):
        raise StateError("Unsupported observed test outcome.")
    return {"outcome": "unverified", **metadata}


def scope_directory(explicit: str | None, scope: dict) -> Path:
    """Choose a stable, isolated directory for one tenant/team/target combination."""
    digest = hashlib.sha256(json.dumps(scope, sort_keys=True).encode("utf-8")).hexdigest()
    return state_directory(explicit) / "records" / digest


def record_resource(metadata: dict, explicit: str | None = None, team: str | None = None,
                    target: str | None = None, verified: bool = False) -> dict:
    """Append an immutable resource observation without a shared-index race.

    ``verified`` means the caller just read the resource from Qyrus. It is not
    a test pass, and it does not remove the need to revalidate before reuse.
    """
    metadata = validate_metadata(metadata)
    scope, secrets = scope_for(explicit, team, target)
    if any(secret in str(value) for secret in secrets for value in (*metadata.values(), *scope.values()) if value):
        raise StateError("A known credential was supplied as metadata; nothing was saved.")
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = {"schema_version": 1, "record_id": uuid.uuid4().hex, "recorded_at": timestamp,
              "scope": scope, "resource": metadata, "verified_at": timestamp if verified else None}
    root = private_directory(state_directory(explicit))
    private_directory(root / "records")
    directory = private_directory(scope_directory(explicit, scope))
    atomic_write_json(directory / f"{record['record_id']}.json", record)
    return record


def list_resources(explicit: str | None = None, team: str | None = None,
                   target: str | None = None, kind: str | None = None) -> list[dict]:
    """Read observations from exactly one scope, never silently merging tenants.

    Omitting target means the unscoped-target bucket, not all application targets.
    Invalid stored data fails closed instead of being rendered in an agent prompt.
    """
    scope, secrets = scope_for(explicit, team, target)
    directory = scope_directory(explicit, scope)
    if not directory.exists():
        return []
    private_directory(state_directory(explicit))
    private_directory(directory.parent)
    private_directory(directory)
    records = []
    try:
        for path in directory.glob("*.json"):
            if path.is_symlink() or not path.is_file():
                raise ValueError
            record = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(record, dict) or set(record) != {"schema_version", "record_id", "recorded_at", "scope", "resource", "verified_at"}
                    or record["schema_version"] != 1 or record["scope"] != scope
                    or not re.fullmatch(r"[0-9a-f]{32}", record["record_id"])):
                raise ValueError
            validate_metadata(record["resource"])
            for field in ("recorded_at", "verified_at"):
                value = record[field]
                if value is None and field == "verified_at":
                    continue
                if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value):
                    raise ValueError
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            if any(secret in str(value) for secret in secrets for value in record["resource"].values()):
                raise ValueError
            if kind is None or record["resource"]["kind"] == kind:
                records.append(record)
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise StateError("Stored Qyrus references are invalid; inspect the private state folder before reusing them.") from None
    return sorted(records, key=lambda item: (item["recorded_at"], item["record_id"]))


def main() -> int:
    """Print a state path, append safe resource metadata, or list scoped references."""
    parser = PrivateArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("path", "record", "list"))
    parser.add_argument("--env-file")
    parser.add_argument("--team")
    parser.add_argument("--target-origin")
    parser.add_argument("--kind", choices=KINDS)
    for field in IDENTIFIERS:
        parser.add_argument("--" + field.replace("_", "-"))
    parser.add_argument("--platform", choices=("web", "mobile", "api"))
    parser.add_argument("--status", choices=STATUSES)
    parser.add_argument("--outcome", choices=OUTCOMES)
    parser.add_argument("--verified", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "path":
            print(str(state_directory(args.env_file)))
        elif args.action == "record":
            metadata = {field: getattr(args, field) for field in FIELDS if getattr(args, field) is not None}
            print(json.dumps(record_resource(metadata, args.env_file, args.team, args.target_origin, args.verified)))
        else:
            if args.verified or any(getattr(args, field) is not None for field in FIELDS - {"kind"}):
                raise StateError("list accepts scope and kind filters only.")
            print(json.dumps(list_resources(args.env_file, args.team, args.target_origin, args.kind)))
        return 0
    except (StateError, SetupError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError:
        print("Cannot access private Qyrus state; check the selected credentials folder and permissions.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

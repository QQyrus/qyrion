"""Register the Qyrus stdio bridge in Antigravity without copying credentials.

Run this from the installed plugin's scripts directory after dependency and
private-file setup. Absolute paths avoid assumptions about host plugin roots.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


class RegistrationError(RuntimeError):
    """Report a safe setup error without printing existing MCP configuration."""


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject duplicate JSON keys instead of silently discarding server entries."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise RegistrationError("The MCP configuration contains duplicate JSON keys; resolve them before setup.")
        result[key] = value
    return result


def server_entry(plugin_root: Path, uv_command: str) -> dict:
    """Resolve a stdio command that reads secrets only through the existing bridge."""
    root = plugin_root.resolve()
    script = root / "scripts" / "qyrus_mcp.py"
    if not script.is_file():
        raise RegistrationError("Run this helper from the complete installed QyrusAI Assure package.")
    executable = shutil.which(uv_command)
    if not executable:
        raise RegistrationError("uv is unavailable; complete the bundled prerequisite setup first.")
    return {
        "command": str(Path(executable).resolve()),
        "args": ["run", "--quiet", "--script", str(script)],
        "cwd": str(root),
    }


def register_server(config_path: Path, entry: dict, *, replace_qyrus: bool = False) -> bool:
    """Atomically merge only Qyrus, preserving other servers and tool restrictions.

    Example:
        register_server(Path.home() / ".gemini/config/mcp_config.json", entry)

    A different existing Qyrus connection needs explicit replacement. The
    return value reports whether the configuration changed, not connectivity.
    """
    path = config_path.expanduser().resolve()
    original = path.read_bytes() if path.exists() else None
    try:
        config = json.loads(original.decode("utf-8-sig"), object_pairs_hook=unique_object) if original is not None else {}
    except (ValueError, UnicodeError):
        raise RegistrationError("The MCP configuration is not valid UTF-8 JSON; it was not changed.") from None
    if not isinstance(config, dict) or not isinstance(config.get("mcpServers", {}), dict):
        raise RegistrationError("Expected an MCP configuration object with an mcpServers object; it was not changed.")
    servers = config.setdefault("mcpServers", {})
    if "qyrus" in servers:
        current = servers["qyrus"]
        if isinstance(current, dict) and all(current.get(key) == value for key, value in entry.items()):
            return False
        if not replace_qyrus:
            raise RegistrationError(
                "A different qyrus MCP entry already exists; it was not changed. "
                "After confirming it is the connection to migrate, rerun with --replace-qyrus."
            )
        entry = dict(entry)
        if isinstance(current, dict):
            for setting in ("disabled", "disabledTools"):
                if setting in current:
                    entry[setting] = current[setting]
    servers["qyrus"] = entry
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            json.dump(config, output, indent=2, ensure_ascii=True)
            output.write("\n")
        # Another setup process may have added a connector since the first read.
        if (path.read_bytes() if path.exists() else None) != original:
            raise RegistrationError("MCP configuration changed during setup; rerun to merge the latest entries.")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def main() -> int:
    """Register Qyrus and report configuration status without claiming authentication."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path.home() / ".gemini/config/mcp_config.json")
    parser.add_argument("--uv", default="uv", help="Verified uv executable name or absolute path")
    parser.add_argument("--replace-qyrus", action="store_true", help="Replace a previously identified Qyrus connection")
    args = parser.parse_args()
    try:
        entry = server_entry(Path(__file__).resolve().parents[1], args.uv)
        changed = register_server(args.config, entry, replace_qyrus=args.replace_qyrus)
        print("Qyrus MCP registration updated." if changed else "Qyrus MCP registration is already current.")
        print("Refresh Antigravity MCP, then verify the Qyrus guide and teams. Registration is not authentication.")
        return 0
    except RegistrationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError:
        print("Cannot read or update the MCP configuration; check its path and file permissions.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

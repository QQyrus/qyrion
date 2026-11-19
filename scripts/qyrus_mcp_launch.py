"""Start the Claude plugin's Qyrus MCP bridge through the shared process launcher."""

import os
from pathlib import Path

from qyrus_process import launch_command


def main() -> int:
    """Run the bridge beside this script and return its exit status."""
    server = Path(__file__).resolve().with_name("qyrus_mcp.py")
    return launch_command(["uv", "run", "--quiet", "--script", str(server)], dict(os.environ))


if __name__ == "__main__":
    raise SystemExit(main())

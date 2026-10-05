# /// script
# requires-python = ">=3.12"
# dependencies = ["fastmcp==4.0.10"]
# ///
"""Bridge the hosted Qyrus MCP to stdio using a private shared dotenv file."""

import logging
import sys

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server import create_proxy

from qyrus_env import SetupError, load_environment


def build_proxy(env: dict[str, str]):
    """Keep the API key in memory and preserve upstream tool names and schemas."""
    transport = StreamableHttpTransport(
        env["QYRUS_MCP_URL"], headers={"X-API-Key": env["QYRUS_API_KEY"]}
    )
    return create_proxy(
        Client(transport, timeout=60, init_timeout=30),
        name="Qyrus Aegis", mask_error_details=True, provider_error_strategy="raise",
    )


def main() -> int:
    """Run a stdio-only proxy without exposing raw transport errors or logs."""
    logging.disable(logging.CRITICAL)
    try:
        proxy = build_proxy(load_environment())
        proxy.run(transport="stdio", show_banner=False)
        return 0
    except SetupError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception:
        print("Qyrus MCP connection failed. Check the private env file and endpoint, then restart MCP.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

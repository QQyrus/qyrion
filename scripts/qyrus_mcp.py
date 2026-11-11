# /// script
# requires-python = ">=3.12"
# dependencies = ["fastmcp==4.0.10", "jsonschema>=4.20,<5"]
# ///
"""Bridge the hosted Qyrus MCP to stdio using a private shared dotenv file.

The hosted server lists 310 tools. By default (`QYRUS_MCP_TOOLS=progressive`)
the bridge offers a host six: the three core tools (`qyrus_guide_get`,
`qyrus_account_capabilities_get`, `qyrus_teams_get_by_api_key`) as direct
proxied tools, plus `qyrus_tools`, `qyrus_tool_schema` and `qyrus_tool_call`
to find, read and call the rest (`qyrus_catalogue.py`; contract in
`docs/plans/qyrus-mcp-progressive-tools.md`). Tools named in
`QYRUS_MCP_PINNED_TOOLS` are also offered directly. `QYRUS_MCP_TOOLS=all`
keeps the full proxy for hosts that do their own deferred tool loading.

The tool list is fixed for the session: no `tools/list_changed`, so a host's
tool prefix (and prompt cache) never changes mid-thread.

Privacy matches the full proxy: the API key stays in memory, logging is off,
and a transport failure reaches the host as a fixed sentence, never the raw
error. It deliberately does not retry, cache results, or write to disk.
"""

import logging
import sys
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError
from fastmcp.server import create_proxy
from fastmcp.tools import ToolResult

from qyrus_catalogue import CORE_TOOLS, SCHEMA_LIMIT, CatalogueCache, CatalogueTool
from qyrus_env import SetupError, load_environment, mcp_tool_settings

DISCLOSURE_TOOLS = ("qyrus_tools", "qyrus_tool_schema", "qyrus_tool_call")
UNREACHABLE = "Qyrus MCP could not be reached. Check the private env file and endpoint, then restart MCP."

PROGRESSIVE_INSTRUCTIONS = (
    "Qyrus has about 300 tools; only a few are listed here. To use another one: "
    "find it with qyrus_tools (browse by service and capability, or search with query), "
    "read its arguments with qyrus_tool_schema, then call it with qyrus_tool_call. "
    "Tools listed directly (qyrus_guide_get and any the person pinned) are called by name. "
    "Call qyrus_guide_get first in a new session."
)

TOOLS_DESCRIPTION = (
    "Find a Qyrus tool among the ones not listed directly. With no arguments: the four services and "
    "their tool counts. With service: its capabilities. With service and capability: its tools, one "
    "line each (name, short description, read/write/delete); five tools or fewer come with their "
    "schemas. With query (words such as \"pause schedule\" or \"latest web run report\"): the best "
    "matches across everything, at most 15. Then read the schema with qyrus_tool_schema and call "
    "with qyrus_tool_call."
)
TOOL_SCHEMA_DESCRIPTION = (
    "Return the full description and input schema of one to five Qyrus tools, exactly as the server "
    "gives them. Read this once before the first qyrus_tool_call to a tool; the schema stays in the "
    "conversation for later calls."
)
TOOL_CALL_DESCRIPTION = (
    "Call any Qyrus tool by name and return its result unchanged. `arguments` are checked against the "
    "tool's input schema first; on a mismatch the schema and the error come back and Qyrus is not "
    "called. Find the name with qyrus_tools and read its schema with qyrus_tool_schema first. "
    "Tools marked delete remove data: call them only when the person asked."
)


def _transport(env: dict[str, str]) -> StreamableHttpTransport:
    """Build the HTTP transport to the hosted server; the key lives only in its headers."""
    return StreamableHttpTransport(env["QYRUS_MCP_URL"], headers={"X-API-Key": env["QYRUS_API_KEY"]})


def _client(env: dict[str, str]) -> Client:
    """Create a fresh upstream client; each catalogue fetch or tool call uses its own session."""
    return Client(_transport(env), timeout=60, init_timeout=30)


def build_proxy(env: dict[str, str]):
    """Return the stdio server: the full proxy, or the six-tool progressive one.

    Example:
        >>> proxy = build_proxy({"QYRUS_MCP_URL": "https://stg-mcp.qyrus.com/mcp", "QYRUS_API_KEY": "k"})  # doctest: +SKIP
        >>> proxy.run(transport="stdio", show_banner=False)  # doctest: +SKIP
    """
    mode, pinned = mcp_tool_settings(env)
    settings: dict[str, Any] = {"name": "Qyrus Aegis", "mask_error_details": True, "provider_error_strategy": "raise"}
    if mode == "progressive":
        settings["instructions"] = PROGRESSIVE_INSTRUCTIONS
    proxy = create_proxy(_client(env), **settings)
    if mode == "all":
        return proxy
    register_disclosure_tools(proxy, env)
    proxy.enable(names={*CORE_TOOLS, *pinned, *DISCLOSURE_TOOLS}, only=True)
    return proxy


async def fetch_catalogue_tools(env: dict[str, str]) -> list[CatalogueTool]:
    """List the upstream tools once; any failure becomes the fixed unreachable sentence."""
    try:
        async with _client(env) as client:
            listed = await client.list_tools()
    except Exception:
        raise ToolError(UNREACHABLE) from None
    return [CatalogueTool(t.name, t.description or "", t.inputSchema or {}) for t in listed]


def register_disclosure_tools(proxy, env: dict[str, str]) -> CatalogueCache:
    """Add `qyrus_tools`, `qyrus_tool_schema` and `qyrus_tool_call` to the proxy.

    The catalogue is fetched with the first call that needs it and cached for
    ten minutes; an unknown name in `qyrus_tool_call` or `qyrus_tool_schema`
    refreshes it once. Returns the cache so tests can inspect it.
    """
    cache = CatalogueCache(lambda: fetch_catalogue_tools(env))
    read_only = {"readOnlyHint": True, "openWorldHint": True}

    @proxy.tool(name="qyrus_tools", description=TOOLS_DESCRIPTION, annotations=read_only)
    async def qyrus_tools(service: str | None = None, capability: str | None = None,
                          query: str | None = None) -> str:
        """Browse or search the Qyrus tool catalogue (see `Catalogue`)."""
        catalogue = await cache.get()
        if query and query.strip():
            return catalogue.render_search(query, service, capability)
        if service and capability:
            return catalogue.browse_capability(service, capability)
        if service:
            return catalogue.browse_service(service)
        return catalogue.overview()

    @proxy.tool(name="qyrus_tool_schema", description=TOOL_SCHEMA_DESCRIPTION, annotations=read_only)
    async def qyrus_tool_schema(names: list[str]) -> str:
        """Return the description and input schema of one to five tools."""
        if not 1 <= len(names) <= SCHEMA_LIMIT:
            raise ToolError(f"Give between 1 and {SCHEMA_LIMIT} tool names.")
        catalogue = await cache.get()
        if not all(catalogue.has(name) for name in names):
            catalogue = await cache.get(refresh=True)
        return catalogue.schemas(names)

    @proxy.tool(name="qyrus_tool_call", description=TOOL_CALL_DESCRIPTION)
    async def qyrus_tool_call(name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        """Check `arguments` against the schema, then call the upstream tool unchanged."""
        catalogue = await cache.get_with_tool(name)
        if catalogue is None:
            raise ToolError(f"No such Qyrus tool: {name}. Use qyrus_tools to find the exact name.")
        arguments = arguments or {}
        problem = catalogue.check_arguments(name, arguments)
        if problem:
            raise ToolError(
                f"Arguments do not match {name}: {problem}. Qyrus was not called.\n"
                + catalogue.schema_block(catalogue.entries[name])
            )
        return await call_upstream(env, name, arguments)

    return cache


async def call_upstream(env: dict[str, str], name: str, arguments: dict[str, Any]) -> ToolResult:
    """Call one upstream tool and relay its content, structured content and error flag unchanged."""
    try:
        async with _client(env) as client:
            result = await client.call_tool(name, arguments, raise_on_error=False)
    except Exception:
        raise ToolError(UNREACHABLE) from None
    return ToolResult(content=result.content, structured_content=result.structured_content,
                      meta=result.meta, is_error=result.is_error)


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

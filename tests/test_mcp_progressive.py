"""End-to-end: the real stdio bridge against a local FastMCP server standing in for Qyrus.

The stand-in has a handful of tools with real input schemas and an access log,
so these tests can say whether the bridge reached "Qyrus" or stopped first.
No test here contacts a Qyrus, staging or production endpoint.
"""

import asyncio
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import NamedTuple

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
API_KEY = "synthetic-bridge-key"

BACKEND = '''
import json, sys
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import uvicorn

port, call_log = int(sys.argv[1]), sys.argv[2]

class Auth(BaseHTTPMiddleware):
    """Require the synthetic X-API-Key on every HTTP request."""
    async def dispatch(self, request, call_next):
        """Check the request header without reflecting its value."""
        if request.headers.get("x-api-key") != "synthetic-bridge-key":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)

server = FastMCP("Fixture")

def record(name, **arguments):
    """Append one upstream call to the access log the test reads."""
    with open(call_log, "a") as handle:
        handle.write(json.dumps({"name": name, "arguments": arguments}) + "\\n")

@server.tool
def qyrus_guide_get(section: str = "index") -> dict:
    """Return a synthetic guide result for the selected section."""
    record("qyrus_guide_get", section=section)
    return {"section": section, "version": "fixture-1"}

@server.tool
def qyrus_teams_get_by_api_key() -> dict:
    """Return the synthetic teams of the key."""
    record("qyrus_teams_get_by_api_key")
    return {"teams": ["team-a"]}

@server.tool
def qyrus_account_capabilities_get() -> dict:
    """Return the synthetic product families."""
    record("qyrus_account_capabilities_get")
    return {"web": "ready"}

@server.tool
def qyrus_web_projects_list(limit: int = 10) -> dict:
    """Lists the projects of the team. Read-only."""
    record("qyrus_web_projects_list", limit=limit)
    return {"projects": ["qbank"][:limit]}

@server.tool
def qyrus_web_script_get(script_id: str, include_steps: bool = False) -> dict:
    """Returns one script by script_id, optionally with its steps."""
    record("qyrus_web_script_get", script_id=script_id, include_steps=include_steps)
    if script_id == "missing":
        raise ToolError("Script not found in this project.")
    return {"script_id": script_id, "steps": [] if include_steps else None}

@server.tool
def qyrus_web_schedule_pause(job_id: str) -> dict:
    """Pauses an active scheduled test job."""
    record("qyrus_web_schedule_pause", job_id=job_id)
    return {"job_id": job_id, "paused": True}

@server.tool
def qyrus_web_steps_delete(script_id: str, step_ids: list[str]) -> dict:
    """Deletes steps from a script permanently."""
    record("qyrus_web_steps_delete", script_id=script_id, step_ids=step_ids)
    return {"deleted": len(step_ids)}

@server.tool
def qyrus_api_assertion_create(script_id: str, assertion_type: str) -> dict:
    """Adds one new assertion to an API script."""
    record("qyrus_api_assertion_create", script_id=script_id, assertion_type=assertion_type)
    return {"created": True}

uvicorn.run(server.http_app(middleware=[Middleware(Auth)]), host="127.0.0.1", port=port, log_level="critical")
'''

CORE = ["qyrus_account_capabilities_get", "qyrus_guide_get", "qyrus_teams_get_by_api_key"]
DISCLOSURE = ["qyrus_tool_call", "qyrus_tool_schema", "qyrus_tools"]
ALL_UPSTREAM = {*CORE, "qyrus_web_projects_list", "qyrus_web_script_get", "qyrus_web_schedule_pause",
                "qyrus_web_steps_delete", "qyrus_api_assertion_create"}


class Upstream(NamedTuple):
    """Where the stand-in Qyrus server listens, its access log and its process."""

    url: str
    call_log: Path
    process: subprocess.Popen


def free_port():
    """Return a TCP port nothing is listening on right now."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def upstream(tmp_path):
    """Run the stand-in Qyrus server and yield its `Upstream`."""
    port = free_port()
    script = tmp_path / "backend.py"
    script.write_text(BACKEND)
    call_log = tmp_path / "calls.jsonl"
    call_log.touch()
    process = subprocess.Popen([sys.executable, str(script), str(port), str(call_log)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                assert process.poll() is None, "Stand-in Qyrus server failed to start"
                assert time.monotonic() < deadline, "Stand-in Qyrus server startup timed out"
                time.sleep(0.05)
        yield Upstream(f"http://127.0.0.1:{port}/mcp", call_log, process)
    finally:
        process.terminate()
        process.wait(timeout=10)


def bridge(url, api_key=API_KEY, **settings):
    """Return a Client talking to the real bridge over stdio; `settings` are bridge env keys."""
    env = {"QYRUS_MCP_URL": url, "QYRUS_API_KEY": api_key, **settings}
    code = (
        "import json, sys; sys.path.insert(0, sys.argv[1]); "
        "from qyrus_mcp import build_proxy; "
        "build_proxy(json.loads(sys.argv[2])).run(transport='stdio', show_banner=False)"
    )
    transport = StdioTransport(command=sys.executable, args=["-c", code, str(SCRIPTS), json.dumps(env)])
    return Client(transport, timeout=30)


def upstream_calls(call_log):
    """Return the {name, arguments} records the stand-in server has served, in order."""
    return [json.loads(line) for line in call_log.read_text().splitlines()]


def text_of(result):
    """Return the text of a tool result's first content block."""
    return result.content[0].text


def test_progressive_mode_lists_the_three_core_and_three_disclosure_tools(upstream):
    url = upstream.url

    async def body():
        async with bridge(url) as client:
            return sorted(tool.name for tool in await client.list_tools())

    assert asyncio.run(body()) == sorted(CORE + DISCLOSURE)


def test_all_mode_lists_every_upstream_tool_unchanged(upstream):
    url = upstream.url

    async def body():
        async with bridge(url, QYRUS_MCP_TOOLS="all") as client:
            return {tool.name for tool in await client.list_tools()}

    assert asyncio.run(body()) == ALL_UPSTREAM


def test_pinned_tools_are_listed_directly_and_the_list_is_fixed_for_the_session(upstream):
    url = upstream.url

    async def body():
        async with bridge(url, QYRUS_MCP_PINNED_TOOLS="qyrus_web_projects_list, qyrus_not_on_the_server") as client:
            before = sorted(tool.name for tool in await client.list_tools())
            await client.call_tool("qyrus_tools", {"query": "pause schedule"})
            await client.call_tool("qyrus_tool_schema", {"names": ["qyrus_web_schedule_pause"]})
            after = sorted(tool.name for tool in await client.list_tools())
            direct = await client.call_tool("qyrus_web_projects_list", {"limit": 1})
        return before, after, direct.data

    before, after, direct = asyncio.run(body())
    assert before == after == sorted(CORE + DISCLOSURE + ["qyrus_web_projects_list"])
    assert direct == {"projects": ["qbank"]}


def test_pinned_tools_are_ignored_in_all_mode(upstream):
    url = upstream.url

    async def body():
        async with bridge(url, QYRUS_MCP_TOOLS="all", QYRUS_MCP_PINNED_TOOLS="qyrus_web_projects_list") as client:
            return {tool.name for tool in await client.list_tools()}

    assert asyncio.run(body()) == ALL_UPSTREAM


def test_core_tools_are_proxied_with_their_upstream_schemas(upstream):
    url = upstream.url

    async def body():
        async with bridge(url) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            result = await client.call_tool("qyrus_guide_get", {"section": "Identifier Map"})
        return tools["qyrus_guide_get"].input_schema, result.data

    schema, data = asyncio.run(body())
    assert schema["properties"]["section"]["default"] == "index"
    assert data == {"section": "Identifier Map", "version": "fixture-1"}


def test_browse_overview_service_capability_and_query(upstream):
    url = upstream.url

    async def body():
        async with bridge(url) as client:
            return (
                text_of(await client.call_tool("qyrus_tools", {})),
                text_of(await client.call_tool("qyrus_tools", {"service": "web"})),
                text_of(await client.call_tool("qyrus_tools", {"service": "web", "capability": "schedule"})),
                text_of(await client.call_tool("qyrus_tools", {"query": "pause schedule"})),
            )

    overview, service, capability, query = asyncio.run(body())
    assert "Qyrus tools: 8 in total, 3 always offered directly." in overview
    assert "- web (4):" in overview and "- api (1):" in overview
    assert "- schedule (1)" not in service and "other (4)" in service  # one-tool capabilities sit under other
    assert "web / schedule — 1 tools:" in capability
    assert "- qyrus_web_schedule_pause [write] — Pauses an active scheduled test job." in capability
    assert "Input schema:" in capability  # five tools or fewer come with their schemas
    assert query.splitlines()[1].startswith("- qyrus_web_schedule_pause [write]")


def test_tool_schema_returns_description_and_input_schema_as_the_server_gives_them(upstream):
    url = upstream.url

    async def body():
        async with bridge(url) as client:
            return text_of(await client.call_tool(
                "qyrus_tool_schema", {"names": ["qyrus_web_script_get", "qyrus_nope"]}))

    text = asyncio.run(body())
    assert "## qyrus_web_script_get [read]" in text
    assert "Returns one script by script_id, optionally with its steps." in text
    schema = json.loads(text.split("Input schema: ")[1].splitlines()[0])
    assert schema["required"] == ["script_id"] and schema["properties"]["include_steps"]["type"] == "boolean"
    assert "No such tool: qyrus_nope" in text


@pytest.mark.parametrize("names", [[], ["qyrus_guide_get"] * 6])
def test_tool_schema_rejects_zero_or_more_than_five_names(upstream, names):
    url = upstream.url

    async def body():
        async with bridge(url) as client:
            await client.call_tool("qyrus_tool_schema", {"names": names})

    with pytest.raises(ToolError, match="between 1 and 5"):
        asyncio.run(body())


def test_tool_call_relays_the_upstream_result_unchanged(upstream):
    url, call_log = upstream.url, upstream.call_log

    async def body():
        async with bridge(url) as client:
            return (await client.call_tool("qyrus_tool_call", {
                "name": "qyrus_web_script_get", "arguments": {"script_id": "s-1", "include_steps": True}})).data

    assert asyncio.run(body()) == {"script_id": "s-1", "steps": []}
    assert upstream_calls(call_log) == [
        {"name": "qyrus_web_script_get", "arguments": {"script_id": "s-1", "include_steps": True}}]


def test_tool_call_with_a_wrong_argument_returns_the_schema_and_never_reaches_qyrus(upstream):
    url, call_log = upstream.url, upstream.call_log

    async def body():
        async with bridge(url) as client:
            await client.call_tool("qyrus_tool_call", {
                "name": "qyrus_web_steps_delete", "arguments": {"script_id": "s-1", "step_ids": "not-a-list"}})

    with pytest.raises(ToolError) as caught:
        asyncio.run(body())
    message = str(caught.value)
    assert "Arguments do not match qyrus_web_steps_delete" in message
    assert "step_ids" in message and "Qyrus was not called" in message
    assert "Input schema:" in message and "[delete]" in message
    assert upstream_calls(call_log) == []


def test_the_mismatch_error_never_quotes_the_argument_value(upstream):
    url, call_log = upstream.url, upstream.call_log
    secret = "sk-live-4f9a-secret-value"

    async def body():
        async with bridge(url) as client:
            await client.call_tool("qyrus_tool_call", {
                "name": "qyrus_web_projects_list", "arguments": {"limit": secret}})

    with pytest.raises(ToolError) as caught:
        asyncio.run(body())
    assert "limit: must be of type integer" in str(caught.value)
    assert secret not in str(caught.value)
    assert upstream_calls(call_log) == []


def test_tool_call_with_a_missing_required_argument_is_caught_before_qyrus(upstream):
    url, call_log = upstream.url, upstream.call_log

    async def body():
        async with bridge(url) as client:
            await client.call_tool("qyrus_tool_call", {"name": "qyrus_web_script_get", "arguments": {}})

    with pytest.raises(ToolError, match="'script_id' is a required property"):
        asyncio.run(body())
    assert upstream_calls(call_log) == []


def test_tool_call_to_an_unknown_name_fails_with_a_pointer_to_qyrus_tools(upstream):
    url, call_log = upstream.url, upstream.call_log

    async def body():
        async with bridge(url) as client:
            await client.call_tool("qyrus_tool_call", {"name": "qyrus_web_script_gett", "arguments": {}})

    with pytest.raises(ToolError, match="No such Qyrus tool: qyrus_web_script_gett. Use qyrus_tools"):
        asyncio.run(body())
    assert upstream_calls(call_log) == []


def test_an_upstream_tool_error_reaches_the_host_as_an_error_result(upstream):
    url = upstream.url

    async def body():
        async with bridge(url) as client:
            return await client.call_tool("qyrus_tool_call", {
                "name": "qyrus_web_script_get", "arguments": {"script_id": "missing"}}, raise_on_error=False)

    result = asyncio.run(body())
    assert result.is_error
    assert "Script not found in this project." in text_of(result)


def test_a_tool_with_no_arguments_can_be_called_without_an_arguments_field(upstream):
    url = upstream.url

    async def body():
        async with bridge(url) as client:
            return (await client.call_tool("qyrus_tool_call", {"name": "qyrus_teams_get_by_api_key"})).data

    assert asyncio.run(body()) == {"teams": ["team-a"]}


def test_a_server_that_goes_away_gives_the_host_a_generic_error_without_the_key_or_address(upstream):
    async def body():
        messages = []
        async with bridge(upstream.url) as client:
            upstream.process.terminate()
            upstream.process.wait(timeout=10)
            for tool, arguments in (("qyrus_tools", {}), ("qyrus_tool_call", {"name": "qyrus_guide_get"})):
                try:
                    await client.call_tool(tool, arguments)
                except Exception as error:
                    messages.append(str(error))
        return messages

    messages = asyncio.run(body())
    assert len(messages) == 2, "both calls must fail once the server is gone"
    for message in messages:
        assert API_KEY not in message and "127.0.0.1" not in message


def test_a_server_that_is_down_at_start_fails_the_connection_without_the_key_or_address():
    dead_url = f"http://127.0.0.1:{free_port()}/mcp"

    async def body():
        async with bridge(dead_url) as client:
            await client.list_tools()

    with pytest.raises(Exception) as caught:
        asyncio.run(body())
    assert API_KEY not in str(caught.value) and "127.0.0.1" not in str(caught.value)


def test_a_rejected_key_gives_the_host_a_generic_error_without_the_key(upstream):
    async def body():
        async with bridge(upstream.url, api_key="wrong-key") as client:
            await client.call_tool("qyrus_tools", {})

    with pytest.raises(Exception) as caught:
        asyncio.run(body())
    assert "wrong-key" not in str(caught.value)


def test_catalogue_fetch_failure_is_one_fixed_sentence_without_the_key_or_address():
    sys.path.insert(0, str(SCRIPTS))
    from qyrus_mcp import fetch_catalogue_tools

    env = {"QYRUS_MCP_URL": f"http://127.0.0.1:{free_port()}/mcp", "QYRUS_API_KEY": API_KEY}
    with pytest.raises(ToolError) as caught:
        asyncio.run(fetch_catalogue_tools(env))
    assert str(caught.value) == "Qyrus MCP could not be reached. Check the private env file and endpoint, then restart MCP."

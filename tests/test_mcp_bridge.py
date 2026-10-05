"""Exercise the real stdio bridge against a loopback MCP server with fake auth."""

import asyncio
from pathlib import Path
import socket
import subprocess
import sys
import time

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def test_stdio_bridge_forwards_guide_and_authenticated_calls(tmp_path):
    """Initialize, discover, and call over stdio plus HTTP without contacting Qyrus."""
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    backend = tmp_path / "backend.py"
    backend.write_text('''
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import uvicorn, sys
class Auth(BaseHTTPMiddleware):
    """Require the synthetic X-API-Key on every HTTP request."""
    async def dispatch(self, request, call_next):
        """Check the request header without reflecting its value."""
        if request.headers.get("x-api-key") != "synthetic-bridge-key":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
server = FastMCP("Fixture")
@server.tool
def qyrus_guide_get(section: str = "index") -> dict:
    """Return a synthetic guide result for the selected section."""
    return {"section": section, "version": "fixture-1"}
uvicorn.run(server.http_app(middleware=[Middleware(Auth)]), host="127.0.0.1", port=int(sys.argv[1]), log_level="critical")
''')
    process = subprocess.Popen([sys.executable, str(backend), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                assert process.poll() is None, "Fixture server failed to start"
                assert time.monotonic() < deadline, "Fixture server startup timed out"
                time.sleep(0.05)
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from qyrus_mcp import build_proxy; "
            "build_proxy({'QYRUS_MCP_URL':sys.argv[2], 'QYRUS_API_KEY':'synthetic-bridge-key'})"
            ".run(transport='stdio', show_banner=False)"
        )

        async def exercise():
            """Verify discovery and a schema-aware tool call survive both transports."""
            transport = StdioTransport(command=sys.executable, args=[
                "-c", code, str(scripts), f"http://127.0.0.1:{port}/mcp",
            ])
            async with Client(transport, timeout=15) as client:
                tools = await client.list_tools()
                assert [tool.name for tool in tools] == ["qyrus_guide_get"]
                result = await client.call_tool("qyrus_guide_get", {"section": "Identifier Map"})
                assert result.data == {"section": "Identifier Map", "version": "fixture-1"}

        asyncio.run(exercise())
    finally:
        process.terminate()
        process.wait(timeout=10)

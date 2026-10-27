from __future__ import annotations

import json
import os
import sys
from contextlib import AsyncExitStack
from datetime import date

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .catalog import ROOT


class CatalogBridge:
    """Real SDK client; starts a separate stdio MCP process and negotiates protocol."""
    def __init__(self, as_of: date | None = None):
        self.as_of = as_of
        self.calls: list[str] = []

    async def __aenter__(self):
        self.stack = AsyncExitStack()
        await self.stack.__aenter__()
        # Least privilege: do not give the catalog process model credentials.
        env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP") if k in os.environ}
        env["PYTHONIOENCODING"] = "utf-8"
        if self.as_of:
            env["IF_AS_OF"] = self.as_of.isoformat()
        try:
            streams = await self.stack.enter_async_context(stdio_client(StdioServerParameters(
                command=sys.executable, args=[str(ROOT / "mcp_server.py")], cwd=str(ROOT), env=env)))
            self.session = await self.stack.enter_async_context(ClientSession(*streams))
            self.initialized = await self.session.initialize()
            listing = await self.session.list_tools()
            self.tools = [t.name for t in listing.tools]
            if not {"search_opportunities", "get_opportunity_details"}.issubset(self.tools):
                raise RuntimeError("MCP catalog did not advertise required tools")
            return self
        except BaseException:
            await self.stack.aclose()
            raise

    async def __aexit__(self, *args):
        return await self.stack.__aexit__(*args)

    async def call(self, name: str, arguments: dict) -> dict:
        if name not in self.tools:
            raise ValueError("MCP tool not allowlisted")
        try:
            result = await self.session.call_tool(name, arguments)
        except Exception:
            raise ValueError("MCP tool call failed; no write was performed by the read-only server") from None
        self.calls.append(name)
        if result.isError:
            raise ValueError("MCP rejected tool arguments or opportunity ID")
        if result.structuredContent:
            return result.structuredContent
        return json.loads("".join(block.text for block in result.content if block.type == "text"))

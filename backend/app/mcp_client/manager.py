"""MCP client manager. Spawns local MCP server subprocesses, keeps ClientSessions
alive for the FastAPI app's lifetime, and routes tool calls to the right server.

Tools are discovered at startup via `session.list_tools()`. The router maps each
tool name to its hosting server so advisors only need to declare `allowed_tools`
by name (no awareness of which server hosts what).
"""

from __future__ import annotations

import json
import logging
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger(__name__)

# backend/ — where `python -m app.mcp_servers.foo` should be run
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class MCPManager:
    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._sessions: dict[str, ClientSession] = {}
        # tool_name -> (server_name, anthropic_spec)
        self._tool_index: dict[str, tuple[str, dict[str, Any]]] = {}

    async def start(self, server_modules: list[str]) -> None:
        self._stack = AsyncExitStack()
        for module in server_modules:
            server_name = module.rsplit(".", 1)[-1]
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", module],
                cwd=str(BACKEND_DIR),
            )
            try:
                streams = await self._stack.enter_async_context(stdio_client(params))
                read, write = streams[0], streams[1]
                session = await self._stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                tools = await session.list_tools()
            except Exception:
                logger.exception("Failed to start MCP server %s", module)
                raise
            self._sessions[server_name] = session
            for tool in tools.tools:
                spec = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema,
                }
                self._tool_index[tool.name] = (server_name, spec)
            logger.info(
                "MCP server '%s' started, tools=%s",
                server_name,
                [t.name for t in tools.tools],
            )

    def known_tools(self) -> list[str]:
        return list(self._tool_index.keys())

    def anthropic_specs(self, names: list[str]) -> list[dict[str, Any]]:
        return [self._tool_index[n][1] for n in names if n in self._tool_index]

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self._tool_index:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "UNKNOWN_TOOL", "message": name},
            }
        server_name, _ = self._tool_index[name]
        session = self._sessions[server_name]
        try:
            result = await session.call_tool(name, arguments)
        except Exception as e:
            logger.exception("Tool call failed: %s(%s)", name, arguments)
            return {
                "ok": False,
                "data": None,
                "error": {"code": "TOOL_ERROR", "message": f"{type(e).__name__}: {e}"},
            }
        # MCP CallToolResult.content is a list of content blocks; for our tools the
        # first TextContent block carries a JSON-encoded payload.
        for block in result.content:
            text = getattr(block, "text", None)
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"ok": True, "data": text, "source": "mcp_text"}
        return {"ok": True, "data": None, "source": "mcp_empty"}

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
        self._sessions.clear()
        self._tool_index.clear()


_manager: MCPManager | None = None


def set_manager(m: MCPManager) -> None:
    global _manager
    _manager = m


def get_manager() -> MCPManager:
    if _manager is None:
        raise RuntimeError("MCP manager not initialized — check FastAPI lifespan")
    return _manager

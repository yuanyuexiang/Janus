"""MCP 客户端管理器。

职责：
- 启动本地 MCP server 子进程（stdio 协议）
- 维持 ClientSession 在 FastAPI 应用生命周期内不断开
- 把工具调用路由到对应的 server

启动时通过 `session.list_tools()` 发现工具，建立 tool_name → server 的索引；
顾问只需要在 `allowed_tools` 里写工具名即可，不必关心它属于哪个 server。
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

# backend/ —— `python -m app.mcp_servers.foo` 的工作目录
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
                logger.exception("启动 MCP server %s 失败", module)
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
                "MCP server '%s' 已启动，工具列表=%s",
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
            logger.exception("工具调用失败: %s(%s)", name, arguments)
            return {
                "ok": False,
                "data": None,
                "error": {"code": "TOOL_ERROR", "message": f"{type(e).__name__}: {e}"},
            }
        # MCP CallToolResult.content 是一组内容块；我们的工具会把 JSON 序列化后
        # 塞在第一个 TextContent 块里。
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
        raise RuntimeError("MCPManager 尚未初始化 —— 检查 FastAPI lifespan 是否正确启动")
    return _manager

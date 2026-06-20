import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.api.settings import router as settings_router
from app.auth import require_access
from app.auth import router as auth_router
from app.config import get_settings
from app.llm import settings_store
from app.mcp_client.manager import MCPManager, set_manager

logger = logging.getLogger(__name__)

settings = get_settings()

MCP_SERVER_MODULES = [
    "app.mcp_servers.market",
    "app.mcp_servers.macro",
    "app.mcp_servers.industry",
    "app.mcp_servers.news",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时把前端配的 LLM 设置载入内存缓存（失败不阻塞启动，走 env 回退）
    try:
        await settings_store.reload()
    except Exception:
        logger.exception("LLM 配置加载失败 —— 走 env 回退")

    manager = MCPManager()
    try:
        await manager.start(MCP_SERVER_MODULES)
    except Exception:
        logger.exception("MCP 启动失败 —— 应用将以无工具模式继续运行")
        await manager.stop()
    set_manager(manager)
    try:
        yield
    finally:
        await manager.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(settings_router)  # 自带 require_access
# 受保护接口：配置了 ACCESS_PASSWORD 后必须带正确 X-Access-Key
app.include_router(chat_router, dependencies=[Depends(require_access)])
app.include_router(conversations_router, dependencies=[Depends(require_access)])


@app.get("/")
async def root() -> dict:
    return {"app": settings.app_name, "env": settings.env}

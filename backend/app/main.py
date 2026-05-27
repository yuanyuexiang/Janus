import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.config import get_settings
from app.mcp_client.manager import MCPManager, set_manager

logger = logging.getLogger(__name__)

settings = get_settings()

MCP_SERVER_MODULES = [
    "app.mcp_servers.market",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = MCPManager()
    try:
        await manager.start(MCP_SERVER_MODULES)
    except Exception:
        logger.exception("MCP startup failed — app will run without tools")
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
app.include_router(chat_router)
app.include_router(conversations_router)


@app.get("/")
async def root() -> dict:
    return {"app": settings.app_name, "env": settings.env}

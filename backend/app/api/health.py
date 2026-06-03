import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.data.datasource import get_data_source
from app.db.session import get_db

router = APIRouter(tags=["health"])


async def _probe_choice() -> dict:
    """best-effort 探活 Choice 网关；网关未配置/不可达都不抛，只返回状态。"""
    settings = get_settings()
    url = settings.choice_gateway_url
    if not url:
        return {"configured": False, "reachable": False, "logged_in": False}
    try:
        async with httpx.AsyncClient(timeout=1.5, trust_env=False) as client:
            r = await client.get(f"{url.rstrip('/')}/healthz")
        if r.status_code != 200:
            return {"configured": True, "reachable": False, "logged_in": False}
        body = r.json()
        return {
            "configured": True,
            "reachable": True,
            "logged_in": bool(body.get("sdk_logged_in")),
        }
    except Exception:
        return {"configured": True, "reachable": False, "logged_in": False}


@router.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    db_ok = False
    try:
        result = await db.execute(text("SELECT 1"))
        db_ok = result.scalar() == 1
    except Exception:
        db_ok = False

    choice = await _probe_choice()
    return {
        "status": "ok",
        "db": db_ok,
        "data_source": {
            "chain": get_data_source().provider_names(),
            "choice": choice,
        },
    }

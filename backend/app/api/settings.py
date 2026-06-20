"""模型配置 API —— 前端按角色配 LLM（model/api_key/api_base）。

- GET  /api/settings/llm        各角色当前配置（key 打码，只回 has_key）
- PUT  /api/settings/llm        保存某角色配置（api_key 空=不改）
- POST /api/settings/llm/test   用给定/已存值测连通性

都挂 require_access 鉴权。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_access
from app.db.repository import get_llm_settings, upsert_llm_setting
from app.db.session import get_db
from app.llm import settings_store
from app.llm.client import test_target
from app.llm.crypto import decrypt, encrypt

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_access)])

ROLES = ("conductor", "advisor", "router")
ROLE_LABELS = {"conductor": "执棋（主持综合）", "advisor": "顾问（默认）", "router": "路由（标题等轻任务）"}


class LlmSettingIn(BaseModel):
    role: str
    model: str
    api_base: str | None = None
    api_key: str | None = None  # 空 / 省略 = 不改动已存的 key


class LlmTestIn(BaseModel):
    role: str
    model: str
    api_base: str | None = None
    api_key: str | None = None


@router.get("/llm")
async def get_llm(db: AsyncSession = Depends(get_db)) -> dict:
    by_role = {r.role: r for r in await get_llm_settings(db)}
    roles = []
    for role in ROLES:
        r = by_role.get(role)
        roles.append(
            {
                "role": role,
                "label": ROLE_LABELS[role],
                "model": (r.model if r else None),
                "api_base": (r.api_base if r else None),
                "has_key": bool(r and r.api_key_enc),
            }
        )
    return {"roles": roles}


@router.put("/llm")
async def put_llm(body: LlmSettingIn, db: AsyncSession = Depends(get_db)) -> dict:
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"未知角色：{body.role}")
    model = body.model.strip()
    if not model:
        raise HTTPException(status_code=400, detail="模型名不能为空")
    api_base = (body.api_base or "").strip() or None
    api_key_enc = encrypt(body.api_key) if body.api_key else None  # 空=不改
    await upsert_llm_setting(
        db, role=body.role, model=model, api_base=api_base, api_key_enc=api_key_enc
    )
    await settings_store.reload()
    return {"ok": True}


@router.post("/llm/test")
async def test_llm(body: LlmTestIn, db: AsyncSession = Depends(get_db)) -> dict:
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"未知角色：{body.role}")
    # api_key 没填则取已存的（让用户「不改 key 只测」也能测）
    key = body.api_key
    if not key:
        by_role = {r.role: r for r in await get_llm_settings(db)}
        r = by_role.get(body.role)
        key = decrypt(r.api_key_enc) if (r and r.api_key_enc) else None
    ok, message = await test_target(body.model.strip(), (body.api_base or "").strip() or None, key)
    return {"ok": ok, "message": message}

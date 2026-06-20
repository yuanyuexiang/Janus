"""设置 API —— 厂商凭据 + 角色分配（前端「设置」二级页对应）。

厂商凭据（模型设置页）：
- GET    /api/settings/credentials              列出（key 打码，含已缓存模型列表）
- PUT    /api/settings/credentials              新增/更新（api_key 空=不改；models 一并入库）
- DELETE /api/settings/credentials/{name}       删除
- POST   /api/settings/credentials/list-models  实时调厂商接口列模型（顺带验 Key）

角色分配（角色设置页，执棋 / 6 位顾问 / 路由 共 8 个）：
- GET    /api/settings/roles                    各角色当前分配的（凭据, 模型）
- PUT    /api/settings/roles                    设置某角色用哪个凭据的哪个模型

离线兜底：
- GET    /api/settings/catalog                  LiteLLM 内置模型目录

都挂 require_access 鉴权。
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_access
from app.db.repository import (
    delete_llm_credential,
    get_llm_credential,
    get_role_assignments,
    list_llm_credentials,
    set_role_assignment,
    upsert_llm_credential,
)
from app.db.session import get_db
from app.llm import settings_store
from app.llm.client import list_models
from app.llm.crypto import decrypt, encrypt
from app.orchestrator.advisors import ALL_ADVISORS, FULL_COUNCIL

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_access)])

# 全部可配角色：执棋 + 6 位顾问（按圆桌顺序）+ 路由
ROLE_META: list[tuple[str, str, str]] = (
    [("conductor", "执棋", "主持 · 综合")]
    + [(n, ALL_ADVISORS[n].profile.display, ALL_ADVISORS[n].profile.role) for n in FULL_COUNCIL]
    + [("router", "路由", "标题等轻任务")]
)
ROLES = {r[0] for r in ROLE_META}


# ---------- 厂商凭据 ----------


class CredentialIn(BaseModel):
    name: str
    provider: str
    api_base: str | None = None
    api_key: str | None = None        # 空 / 省略 = 不改动已存 key
    models: list[str] | None = None   # 实时拉到的模型列表（None = 不改）


class ListModelsIn(BaseModel):
    provider: str
    api_base: str | None = None
    api_key: str | None = None        # 没传则用已存凭据的 key（按 name 取）
    name: str | None = None


@router.get("/credentials")
async def get_credentials(db: AsyncSession = Depends(get_db)) -> dict:
    out = [
        {
            "name": c.name,
            "provider": c.provider,
            "api_base": c.api_base,
            "has_key": bool(c.api_key_enc),
            "models": c.models or [],
        }
        for c in await list_llm_credentials(db)
    ]
    return {"credentials": out}


@router.put("/credentials")
async def put_credential(body: CredentialIn, db: AsyncSession = Depends(get_db)) -> dict:
    name = body.name.strip()
    provider = body.provider.strip()
    if not name:
        raise HTTPException(status_code=400, detail="凭据名称不能为空")
    if not provider:
        raise HTTPException(status_code=400, detail="请选择厂商")
    api_key_enc = encrypt(body.api_key) if body.api_key else None
    await upsert_llm_credential(
        db,
        name=name,
        provider=provider,
        api_base=(body.api_base or "").strip() or None,
        api_key_enc=api_key_enc,
        models=body.models,
    )
    await settings_store.reload()
    return {"ok": True}


@router.delete("/credentials/{name}")
async def remove_credential(name: str, db: AsyncSession = Depends(get_db)) -> dict:
    await delete_llm_credential(db, name)
    await settings_store.reload()
    return {"ok": True}


@router.post("/credentials/list-models")
async def live_list_models(body: ListModelsIn, db: AsyncSession = Depends(get_db)) -> dict:
    """实时调厂商接口列出该账号可用模型（顺带验证 Key）。"""
    key = body.api_key
    if not key and body.name:
        existing = await get_llm_credential(db, body.name)
        key = decrypt(existing.api_key_enc) if (existing and existing.api_key_enc) else None
    ok, models, message = await list_models(
        body.provider, (body.api_base or "").strip() or None, key
    )
    return {"ok": ok, "models": models, "message": message}


# ---------- 角色分配（角色 → 凭据 + 模型）----------


class RoleAssignIn(BaseModel):
    role: str
    credential_name: str | None = None  # None / 空 = 清除分配
    model: str | None = None


@router.get("/roles")
async def get_roles(db: AsyncSession = Depends(get_db)) -> dict:
    assigned = {a.role: a for a in await get_role_assignments(db)}
    roles = [
        {
            "role": r,
            "label": label,
            "tag": tag,
            "credential": assigned[r].credential_name if r in assigned else None,
            "model": assigned[r].model if r in assigned else None,
        }
        for (r, label, tag) in ROLE_META
    ]
    return {"roles": roles}


@router.put("/roles")
async def put_role(body: RoleAssignIn, db: AsyncSession = Depends(get_db)) -> dict:
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"未知角色：{body.role}")
    cred = (body.credential_name or "").strip() or None
    model = (body.model or "").strip() or None
    if cred is not None and await get_llm_credential(db, cred) is None:
        raise HTTPException(status_code=400, detail=f"凭据「{cred}」不存在")
    await set_role_assignment(db, role=body.role, credential_name=cred, model=model)
    await settings_store.reload()
    return {"ok": True}


# ---------- 模型目录（LiteLLM 内置，离线兜底）----------


@lru_cache(maxsize=1)
def _catalog() -> dict[str, list[str]]:
    """从 LiteLLM 的 model_cost 取所有对话模型（mode==chat），按厂商分组、
    剥掉「厂商/」前缀、去掉微调/容器等噪声，排序。结果缓存（目录是静态的）。"""
    import litellm

    grouped: dict[str, set[str]] = defaultdict(set)
    for full, meta in litellm.model_cost.items():
        if not isinstance(meta, dict) or meta.get("mode") != "chat":
            continue
        prov = meta.get("litellm_provider")
        if not prov:
            continue
        short = full.split("/", 1)[1] if full.startswith(prov + "/") else full
        if ":" in short or short in ("container",):
            continue
        grouped[prov].add(short)
    return {p: sorted(v) for p, v in grouped.items()}


@router.get("/catalog")
async def get_catalog() -> dict:
    return {"catalog": _catalog()}

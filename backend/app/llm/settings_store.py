"""LLM 配置内存缓存：厂商凭据 + 角色分配。

启动时 reload() 一次；前端改配置后再 reload()。resolve(role) 同步读这里。
明文 api_key 只存内存、不落日志。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 凭据：name -> {"provider": str, "api_base": str|None, "api_key": str|None, "models": list[str]}
_creds: dict[str, dict] = {}
# 角色分配：role -> {"credential": str|None, "model": str|None}
_roles: dict[str, dict] = {}


async def reload() -> None:
    from app.db.repository import get_role_assignments, list_llm_credentials
    from app.db.session import SessionLocal
    from app.llm.crypto import decrypt

    new_creds: dict[str, dict] = {}
    new_roles: dict[str, dict] = {}
    try:
        async with SessionLocal() as db:
            for c in await list_llm_credentials(db):
                new_creds[c.name] = {
                    "provider": c.provider,
                    "api_base": c.api_base,
                    "api_key": decrypt(c.api_key_enc) if c.api_key_enc else None,
                    "models": c.models or [],
                }
            for a in await get_role_assignments(db):
                new_roles[a.role] = {"credential": a.credential_name, "model": a.model}
    except Exception:
        logger.exception("加载 LLM 配置失败，沿用旧缓存")
        return
    _creds.clear()
    _creds.update(new_creds)
    _roles.clear()
    _roles.update(new_roles)
    logger.info(
        "LLM 配置已加载：凭据=%s 角色分配=%s",
        list(_creds),
        {r: v.get("credential") for r, v in _roles.items()},
    )


def resolve(role: str) -> dict | None:
    """该角色实际生效的 {provider, model, api_base, api_key}；
    未分配 / 所指凭据不存在 / 没选模型，返回 None。"""
    assign = _roles.get(role)
    if not assign or not assign.get("credential") or not assign.get("model"):
        return None
    cred = _creds.get(assign["credential"])
    if not cred:
        return None
    return {
        "provider": cred["provider"],
        "model": assign["model"],
        "api_base": cred.get("api_base"),
        "api_key": cred.get("api_key"),
    }

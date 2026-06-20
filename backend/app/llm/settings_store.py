"""LLM 配置的内存缓存。

启动时 reload() 一次；前端保存配置后再 reload()。resolve_target 同步读这里，
避免每次 LLM 调用都打 DB。键已解密好（明文 api_key 只存内存，不落日志）。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# role -> {"model": str|None, "api_base": str|None, "api_key": str|None}
_cache: dict[str, dict[str, str | None]] = {}


async def reload() -> None:
    # 延迟 import，避免模块级循环依赖
    from app.db.repository import get_llm_settings
    from app.db.session import SessionLocal
    from app.llm.crypto import decrypt

    new: dict[str, dict[str, str | None]] = {}
    try:
        async with SessionLocal() as db:
            for row in await get_llm_settings(db):
                new[row.role] = {
                    "model": row.model,
                    "api_base": row.api_base,
                    "api_key": decrypt(row.api_key_enc) if row.api_key_enc else None,
                }
    except Exception:
        logger.exception("加载 LLM 配置失败，沿用旧缓存 / env 回退")
        return
    _cache.clear()
    _cache.update(new)
    logger.info("LLM 配置已加载：%s", list(_cache.keys()))


def get(role: str) -> dict[str, str | None] | None:
    return _cache.get(role)

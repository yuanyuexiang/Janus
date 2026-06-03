"""访问密钥鉴权 —— 防陌生人滥用。

设计：
- 配置 ACCESS_PASSWORD（非空）后，受保护接口（/api/chat、/api/conversations）
  必须带 `X-Access-Key` 请求头且与之匹配，否则 401。
- ACCESS_PASSWORD 为空 → 不设防（本地开发方便）。
- 用 hmac.compare_digest 做常量时间比较，避免计时侧信道。

这是后端强制校验 —— 前端密码框只是入口体验，真正拦截在这里，
直接打 API 也绕不过去。
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import get_settings


async def require_access(x_access_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    pw = settings.access_password
    if not pw:
        return  # 未配置访问密钥 → 开放
    if not x_access_key or not hmac.compare_digest(x_access_key, pw):
        raise HTTPException(status_code=401, detail="访问密钥无效")


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
async def auth_status() -> dict:
    """前端用来判断是否需要解锁（不暴露密码本身）。"""
    return {"required": bool(get_settings().access_password)}


@router.get("/check", dependencies=[Depends(require_access)])
async def auth_check() -> dict:
    """带正确 X-Access-Key 才返回 200，供前端验证密码。"""
    return {"ok": True}

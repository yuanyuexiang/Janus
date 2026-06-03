"""访问密钥鉴权 + 改密码 —— 防陌生人滥用。

设计：
- 单一共享访问密码。受保护接口（/api/chat、/api/conversations）必须带
  `X-Access-Key` 头且匹配，否则 401。后端强制校验，直接打 API 也绕不过。
- 密码来源优先级：data/access.json（改过密码后）> ACCESS_PASSWORD 环境变量。
  两者都没有 → 不设防（本地开发）。
- 落盘只存 pbkdf2 哈希 + 随机盐，不存明文；常量时间比较防计时侧信道。
- data/ 已 gitignore，不进版本库。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import get_settings

_STORE = Path(__file__).resolve().parent.parent / "data" / "access.json"
_ITERATIONS = 200_000
_MIN_LEN = 4


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS).hex()


def _load() -> dict | None:
    """读取已落盘的密码哈希（改过密码才有）。"""
    try:
        if _STORE.exists():
            return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def _save(password: str) -> None:
    salt = secrets.token_bytes(16)
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(
        json.dumps({"salt": salt.hex(), "hash": _hash(password, salt)}),
        encoding="utf-8",
    )


def is_protection_on() -> bool:
    """是否启用了访问密码（落盘哈希或环境变量任一存在）。"""
    return _load() is not None or bool(get_settings().access_password)


def password_matches(candidate: str) -> bool:
    """候选密码是否匹配当前生效密码。未设密码时恒为 True（开放）。"""
    stored = _load()
    if stored:
        try:
            salt = bytes.fromhex(stored["salt"])
            return hmac.compare_digest(_hash(candidate, salt), stored["hash"])
        except Exception:
            return False
    env_pw = get_settings().access_password
    if not env_pw:
        return True  # 未设防
    return hmac.compare_digest(candidate, env_pw)


async def require_access(x_access_key: str | None = Header(default=None)) -> None:
    if not is_protection_on():
        return
    if not x_access_key or not password_matches(x_access_key):
        raise HTTPException(status_code=401, detail="访问密钥无效")


router = APIRouter(prefix="/api/auth", tags=["auth"])


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


@router.get("/status")
async def auth_status() -> dict:
    """前端用来判断是否需要解锁（不暴露密码本身）。"""
    return {"required": is_protection_on()}


@router.get("/check", dependencies=[Depends(require_access)])
async def auth_check() -> dict:
    """带正确 X-Access-Key 才返回 200，供前端验证密码。"""
    return {"ok": True}


@router.post("/change")
async def change_password(body: ChangePasswordBody) -> dict:
    """改密码：校验当前密码 → 落盘新密码哈希。
    校验当前密码本身即是鉴权（知道当前密码才能改）。"""
    if not is_protection_on():
        raise HTTPException(status_code=400, detail="未启用访问密码，无需修改")
    if not password_matches(body.current_password):
        raise HTTPException(status_code=401, detail="当前密码不正确")
    new_pw = body.new_password.strip()
    if len(new_pw) < _MIN_LEN:
        raise HTTPException(status_code=400, detail=f"新密码至少 {_MIN_LEN} 位")
    if password_matches(new_pw):
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    _save(new_pw)
    return {"ok": True}

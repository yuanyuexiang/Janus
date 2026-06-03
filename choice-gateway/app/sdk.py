"""SDK 单例封装。

设计目的：
- 整个 gateway 进程**只有一个** EmQuantAPI 登录态，避免抢设备配额
- 把同步 SDK 调用包装成异步 helper（FastAPI handler 直接 await）
- 启动登录优先级：
    1. CHOICE_USER + CHOICE_PASSWORD 都有 → 账密直登（ForceLogin=1，每次启动重登；不写 userInfo）
    2. libs/{linux,mac}/x64/userInfo 存在 → 静默登录（首次靠 SMS 激活生成）
    3. 都没有 → 保持 unauth 状态，等 /api/activate 走 SXDL 短信激活
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SDKStatus:
    available: bool          # SDK 二进制能 import 吗
    logged_in: bool          # c.start 成功了吗
    last_error: str | None = None  # 最近一次失败原因（用于 /healthz 展示）


# 全局状态 + 单线程互斥（EmQuantAPI 是同步、单线程的 C 库）
_status = SDKStatus(available=False, logged_in=False)
_lock = threading.RLock()
_c: Any = None  # 真正 import 进来后是 EmQuantAPI.c 类


def _try_import() -> None:
    """惰性 import SDK；失败把 last_error 记上就退出。"""
    global _c
    if _c is not None:
        return
    try:
        from EmQuantAPI import c  # type: ignore[import-not-found]

        _c = c
        _status.available = True
        logger.info("EmQuantAPI 已 import")
    except Exception as e:
        _status.available = False
        _status.last_error = f"import 失败：{type(e).__name__}: {e}"
        logger.exception("EmQuantAPI import 失败")


def get_status() -> SDKStatus:
    return _status


def _login_with_userinfo() -> bool:
    """没参数的 c.start() —— 读 SDK 目录下的 userInfo 文件登录。"""
    _try_import()
    if not _status.available:
        return False
    try:
        result = _c.start()
        if result.ErrorCode == 0:
            _status.logged_in = True
            _status.last_error = None
            logger.info("Choice SDK 登录成功（userInfo 模式）")
            return True
        _status.logged_in = False
        _status.last_error = f"userInfo 登录失败：code={result.ErrorCode} msg={result.ErrorMsg!r}"
        logger.warning(_status.last_error)
        return False
    except Exception as e:
        _status.logged_in = False
        _status.last_error = f"userInfo 登录异常：{type(e).__name__}: {e}"
        logger.exception("Choice userInfo 登录抛异常")
        return False


def _login_with_credentials(user: str, password: str) -> bool:
    """账密直登：ForceLogin=1,UserName=...,Password=...
    注意：此模式不会写 userInfo，每次进程启动都需要重登。
    适用于：账号已开通量化接口、不想/无法走 SMS 流程的服务化场景。"""
    _try_import()
    if not _status.available:
        return False
    try:
        result = _c.start(f"ForceLogin=1,UserName={user},Password={password}")
        if result.ErrorCode == 0:
            _status.logged_in = True
            _status.last_error = None
            logger.info("Choice SDK 登录成功（账密模式）")
            return True
        _status.logged_in = False
        _status.last_error = f"账密登录失败：code={result.ErrorCode} msg={result.ErrorMsg!r}"
        logger.warning(_status.last_error)
        return False
    except Exception as e:
        _status.logged_in = False
        _status.last_error = f"账密登录异常：{type(e).__name__}: {e}"
        logger.exception("Choice 账密登录抛异常")
        return False


def try_auto_login() -> bool:
    """启动时调用。优先级：账密 > userInfo > 等 SMS 激活。"""
    with _lock:
        if not _status.available:
            _try_import()
        if not _status.available:
            return False

        # 1. 账密直登（适合服务化部署，账号已开通量化权限的场景）
        user = os.environ.get("CHOICE_USER", "").strip()
        password = os.environ.get("CHOICE_PASSWORD", "").strip()
        if user and password:
            return _login_with_credentials(user, password)

        # 2. userInfo 静默登录（SMS 激活过一次后会生成）
        # SDK 不直接暴露 userInfo 路径，实践中放在 libs/{os}/{arch}/ 下
        sdk_dir = _find_sdk_base()
        if sdk_dir:
            candidates = [
                os.path.join(sdk_dir, "libs", "linux", "x64", "userInfo"),
                os.path.join(sdk_dir, "libs", "mac", "userInfo"),
            ]
            if any(os.path.exists(p) for p in candidates):
                return _login_with_userinfo()

        logger.info("未配置账密、也无 userInfo 令牌；请通过 /api/activate 走短信激活")
        return False


def _find_sdk_base() -> str | None:
    """从 sys.path 找 EmQuantAPI.pth 里指向的 SDK base 目录。"""
    import sys
    for spath in sys.path:
        pth = os.path.join(spath, "EmQuantAPI.pth")
        if os.path.exists(pth):
            with open(pth, encoding="utf-8") as f:
                base = f.readline().strip()
            if base and os.path.isdir(base):
                return base
    return None


def activate_sms(phone: str) -> tuple[bool, str]:
    """上行短信激活：必须先用绑定手机发 SXDL 到 9535711（10 分钟内）。
    成功后 SDK 自动写 userInfo，下次进程启动 try_auto_login 直接用。"""
    with _lock:
        _try_import()
        if not _status.available:
            return False, _status.last_error or "SDK 不可用"
        try:
            result = _c.start(f"LoginMode=SXDL,PhoneNumber={phone}")
        except Exception as e:
            _status.last_error = f"activate 异常：{type(e).__name__}: {e}"
            logger.exception("activate_sms 抛异常")
            return False, _status.last_error
        if result.ErrorCode == 0:
            _status.logged_in = True
            _status.last_error = None
            logger.info("Choice SDK 激活成功，userInfo 已写入")
            return True, "ok"
        _status.logged_in = False
        _status.last_error = f"激活失败：code={result.ErrorCode} msg={result.ErrorMsg!r}"
        logger.warning(_status.last_error)
        return False, _status.last_error


def shutdown() -> None:
    """进程退出时调用，断开 SDK 会话。"""
    with _lock:
        if _c is not None and _status.logged_in:
            try:
                _c.stop()
            except Exception:
                logger.exception("c.stop() 抛异常（忽略）")
        _status.logged_in = False


# ---------- 业务调用 helpers（同步 → 异步包一层）----------


def _ensure_ready() -> None:
    if not _status.logged_in:
        raise RuntimeError("Choice SDK 未登录（先调 /api/activate 或确认 userInfo 存在）")


def _call_sync(fn_name: str, *args: Any, **kwargs: Any) -> Any:
    """通用同步调用入口；调 c.{fn_name}(*args, **kwargs)。"""
    with _lock:
        _ensure_ready()
        fn = getattr(_c, fn_name)
        result = fn(*args, **kwargs)
        if result.ErrorCode != 0:
            raise RuntimeError(
                f"c.{fn_name} 返回错误：code={result.ErrorCode} msg={result.ErrorMsg!r}"
            )
        return result


async def call(fn_name: str, *args: Any, **kwargs: Any) -> Any:
    """异步入口：把同步调用扔进 thread executor 不阻塞事件循环。"""
    return await asyncio.to_thread(_call_sync, fn_name, *args, **kwargs)

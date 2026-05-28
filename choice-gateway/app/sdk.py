"""SDK 单例封装。

设计目的：
- 整个 gateway 进程**只有一个** EmQuantAPI 登录态，避免抢设备配额
- 把同步 SDK 调用包装成异步 helper（FastAPI handler 直接 await）
- 启动时若已有 userInfo 令牌则自动登录；没有就保持 unauth 状态，等
  /api/activate 触发短信激活
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


def try_auto_login() -> bool:
    """启动时调用。如果 SDK 目录里已经有 userInfo，会自动登录；否则保持
    available=True logged_in=False，等用户走 /api/activate。"""
    with _lock:
        # 容器内的 SDK 目录可能不在 sys.path —— 通过 PYTHONPATH 注入
        # （Dockerfile 已 ENV PYTHONPATH=/sdk）
        if not _status.available:
            _try_import()
        if not _status.available:
            return False

        # 仅当 SDK 目录下找得到 userInfo 才尝试自动登录
        # SDK 不直接暴露 userInfo 路径，但实践中它在 libs/{os}/{arch}/ 下
        sdk_dir = os.environ.get("PYTHONPATH", "").split(":")[0] or "."
        candidates = [
            os.path.join(sdk_dir, "libs", "linux", "x64", "userInfo"),
            os.path.join(sdk_dir, "libs", "mac", "userInfo"),
        ]
        if not any(os.path.exists(p) for p in candidates):
            logger.info("未找到 userInfo 令牌，跳过自动登录；请通过 /api/activate 激活")
            return False

        return _login_with_userinfo()


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

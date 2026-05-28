"""统一响应信封：和 backend DataSource 的语义保持完全一致。"""

from datetime import datetime, timezone
from typing import Any, TypedDict


class Envelope(TypedDict):
    ok: bool
    data: Any | None
    source: str | None
    as_of: str
    error: dict | None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ok(data: Any, source: str = "choice") -> Envelope:
    return {"ok": True, "data": data, "source": source, "as_of": now_iso(), "error": None}


def err(code: str, message: str, http_status: int = 200) -> tuple[Envelope, int]:
    """返回 (envelope, http_status)。
    HTTP 状态码区分：
      200 业务级错误（unsupported indicator 等）
      503 SDK 未就绪
      504 SDK 调用超时
    """
    return (
        {
            "ok": False,
            "data": None,
            "source": None,
            "as_of": now_iso(),
            "error": {"code": code, "message": message},
        },
        http_status,
    )

"""所有数据 provider + MCP 工具共用的响应信封。

形状沿用 v2 §6.5 约定的 MCP 工具输出协议：
`{ ok, data, source, as_of, error }`。当 provider 没有对应数据时返回 None，
让 DataSource 继续往下一个 provider 探。
"""

from datetime import datetime, timezone
from typing import Any, TypedDict


class DataError(TypedDict):
    code: str
    message: str


class DataEnvelope(TypedDict):
    ok: bool
    data: Any | None
    source: str | None
    as_of: str
    error: DataError | None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ok(data: Any, source: str) -> DataEnvelope:
    return {"ok": True, "data": data, "source": source, "as_of": now_iso(), "error": None}


def err(code: str, message: str) -> DataEnvelope:
    return {
        "ok": False,
        "data": None,
        "source": None,
        "as_of": now_iso(),
        "error": {"code": code, "message": message},
    }

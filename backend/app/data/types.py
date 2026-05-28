"""Shared response envelope used by all data providers + MCP tools.

The shape mirrors the MCP tool output convention agreed in v2 §6.5:
`{ ok, data, source, as_of, error }`. Providers return None when they
don't have the requested data so DataSource can fall through.
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

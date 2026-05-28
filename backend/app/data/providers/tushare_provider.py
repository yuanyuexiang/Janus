"""Tushare Pro HTTP provider.

Tushare Pro uses a single JSON-RPC-ish POST endpoint where `api_name`, `token`,
`params`, and `fields` are body fields. Reference: https://tushare.pro/document/2

M3 v1 implements:
  - get_price → daily_basic (PE/PB/close/turnover_rate/circ_mv)

Macro / industry endpoints come in M3.1 once we know which exact ones to call.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.data.providers.base import DataProvider

logger = logging.getLogger(__name__)

TUSHARE_URL = "https://api.tushare.pro"

# Symbol normalization: 600519 → 600519.SH, 000001 → 000001.SZ, 300750 → 300750.SZ
# A-share tickers: 6xx → SH, 0xx / 3xx → SZ, 8xx / 4xx → BJ
def _normalize_ts_code(symbol: str) -> str | None:
    s = symbol.upper().strip()
    if "." in s:
        return s
    if re.fullmatch(r"\d{6}", s):
        first = s[0]
        if first == "6":
            return f"{s}.SH"
        if first in ("0", "3"):
            return f"{s}.SZ"
        if first in ("8", "4"):
            return f"{s}.BJ"
    # US tickers (AAPL etc) — Tushare doesn't cover, signal "skip me"
    return None


class TushareProvider(DataProvider):
    name = "tushare"

    def __init__(self, token: str, timeout: float = 5.0) -> None:
        self.token = token
        self.timeout = timeout
        # Cache `name` once we successfully fetch it (small dict, no eviction needed for MVP)
        self._name_cache: dict[str, str] = {}

    async def _call(self, api_name: str, params: dict[str, Any], fields: str = "") -> list[dict]:
        """Low-level Tushare call. Returns list of dicts keyed by field names.
        Raises on HTTP error or non-zero code."""
        payload = {
            "api_name": api_name,
            "token": self.token,
            "params": params,
            "fields": fields,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(TUSHARE_URL, json=payload)
        r.raise_for_status()
        body = r.json()
        if body.get("code") != 0:
            raise RuntimeError(f"tushare {api_name}: {body.get('msg', 'unknown error')}")
        data = body.get("data") or {}
        cols = data.get("fields") or []
        items = data.get("items") or []
        return [dict(zip(cols, row)) for row in items]

    async def _resolve_name(self, ts_code: str) -> str | None:
        if ts_code in self._name_cache:
            return self._name_cache[ts_code]
        try:
            rows = await self._call(
                "stock_basic",
                params={"ts_code": ts_code},
                fields="ts_code,name,industry",
            )
        except Exception as e:
            logger.warning("tushare stock_basic %s failed: %s", ts_code, e)
            return None
        if not rows:
            return None
        name = rows[0].get("name")
        if name:
            self._name_cache[ts_code] = name
        return name

    async def get_price(self, symbol: str) -> dict | None:
        ts_code = _normalize_ts_code(symbol)
        if not ts_code:
            return None  # not an A-share; let mock handle (e.g. AAPL)

        # daily_basic returns latest record if `trade_date` not given,
        # but the free tier sometimes restricts. Try without first, walk back if needed.
        rows: list[dict] = []
        try:
            rows = await self._call(
                "daily_basic",
                params={"ts_code": ts_code},
                fields="ts_code,trade_date,close,pe,pb,total_share,circ_mv,turnover_rate",
            )
        except Exception as e:
            logger.warning("tushare daily_basic %s failed: %s", ts_code, e)
            return None

        if not rows:
            # Walk back up to 7 calendar days to find the latest trade day
            for offset in range(1, 8):
                d = (datetime.utcnow() - timedelta(days=offset)).strftime("%Y%m%d")
                try:
                    rows = await self._call(
                        "daily_basic",
                        params={"ts_code": ts_code, "trade_date": d},
                        fields="ts_code,trade_date,close,pe,pb,total_share,circ_mv,turnover_rate",
                    )
                except Exception:
                    continue
                if rows:
                    break

        if not rows:
            return None

        # Most-recent first
        rows.sort(key=lambda r: r.get("trade_date") or "", reverse=True)
        latest = rows[0]

        # Optionally fetch previous-day close for change_pct (if today's row already has change_pct via `daily` API).
        # For brevity we'll attempt the `daily` endpoint to get pct_chg.
        change_pct: float | None = None
        try:
            daily_rows = await self._call(
                "daily",
                params={"ts_code": ts_code, "trade_date": latest.get("trade_date")},
                fields="ts_code,trade_date,close,pct_chg",
            )
            if daily_rows:
                change_pct = daily_rows[0].get("pct_chg")
        except Exception as e:
            logger.debug("tushare daily fallback %s failed: %s", ts_code, e)

        name = await self._resolve_name(ts_code)

        return {
            "symbol": ts_code,
            "name": name,
            "price": latest.get("close"),
            "change_pct": change_pct,
            "pe": latest.get("pe"),
            "pb": latest.get("pb"),
            "trade_date": latest.get("trade_date"),
            "turnover_rate": latest.get("turnover_rate"),
            "circ_mv": latest.get("circ_mv"),
        }

    # Macro & industry coverage deferred to M3.1; let MockProvider handle them.

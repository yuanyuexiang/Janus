"""Tushare Pro HTTP provider.

Tushare Pro uses a single JSON-RPC-ish POST endpoint where `api_name`, `token`,
`params`, and `fields` are body fields. Reference: https://tushare.pro/document/2

Endpoints covered:
  - get_price            → daily_basic + daily      (often requires score≥600)
  - get_macro_indicator  → cn_m / cn_ppi / cn_pmi / sf_month  (free tier OK)

Endpoints we attempted but the default-tier token can't reach (40203 perm error)
fall through to MockProvider transparently:
  - stock_basic / daily / daily_basic / cn_cpi / cn_gdp / index_basic / index_daily
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
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

    # In-process cache: tushare's free tier limits most endpoints to 1 req/hour,
    # so we cache results for an hour by (api_name, sorted_params).
    _cache: dict[str, tuple[float, list[dict]]] = {}
    _cache_lock = asyncio.Lock()

    def __init__(self, token: str, timeout: float = 5.0, cache_ttl: float = 3600.0) -> None:
        self.token = token
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._name_cache: dict[str, str] = {}

    @staticmethod
    def _cache_key(api_name: str, params: dict) -> str:
        return f"{api_name}:{json.dumps(params, sort_keys=True, ensure_ascii=False)}"

    async def _call(self, api_name: str, params: dict[str, Any], fields: str = "") -> list[dict]:
        """Low-level Tushare call with 1-hour cache. Raises on HTTP error or non-zero code."""
        key = self._cache_key(api_name, params)
        now = time.monotonic()
        async with self._cache_lock:
            cached = self._cache.get(key)
            if cached and now - cached[0] < self.cache_ttl:
                return cached[1]

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
        rows = [dict(zip(cols, row)) for row in items]

        async with self._cache_lock:
            self._cache[key] = (now, rows)
        return rows

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

    # ---------- Macro ----------

    async def get_macro_indicator(self, indicator: str) -> dict | None:
        """Wire the indicators we have Tushare access to. Others (cpi/gdp/fx/etc)
        return None so MockProvider can answer them.
        """
        key = indicator.lower().strip()
        try:
            if key == "m2":
                return await self._fetch_m2()
            if key == "ppi":
                return await self._fetch_ppi()
            if key == "pmi_manufacturing":
                return await self._fetch_pmi_manufacturing()
            if key == "social_financing":
                return await self._fetch_social_financing()
        except Exception as e:
            logger.warning("tushare macro %s failed: %s", key, e)
            return None
        return None  # fall through to next provider

    async def _fetch_m2(self) -> dict | None:
        rows = await self._call(
            "cn_m", params={}, fields="month,m2_yoy,m1_yoy,m0_yoy"
        )
        if not rows:
            return None
        rows.sort(key=lambda r: r.get("month") or "", reverse=True)
        latest = rows[0]
        prev = rows[1] if len(rows) > 1 else None
        m2 = latest.get("m2_yoy")
        prev_m2 = prev.get("m2_yoy") if prev else None
        trend = _describe_yoy_trend("M2", m2, prev_m2)
        return {
            "name": "M2 同比",
            "value": m2,
            "unit": "%",
            "period": _format_month(latest.get("month")),
            "trend": trend,
            "detail": {
                "m1_yoy": latest.get("m1_yoy"),
                "m0_yoy": latest.get("m0_yoy"),
            },
        }

    async def _fetch_ppi(self) -> dict | None:
        rows = await self._call(
            "cn_ppi", params={}, fields="month,ppi_yoy,ppi_mp_yoy"
        )
        if not rows:
            return None
        rows.sort(key=lambda r: r.get("month") or "", reverse=True)
        latest = rows[0]
        prev = rows[1] if len(rows) > 1 else None
        ppi = latest.get("ppi_yoy")
        trend = _describe_yoy_trend("PPI", ppi, prev.get("ppi_yoy") if prev else None)
        return {
            "name": "PPI 同比",
            "value": ppi,
            "unit": "%",
            "period": _format_month(latest.get("month")),
            "trend": trend,
            "detail": {"生产资料 yoy": latest.get("ppi_mp_yoy")},
        }

    async def _fetch_pmi_manufacturing(self) -> dict | None:
        rows = await self._call(
            "cn_pmi", params={}, fields="month,pmi010000"
        )
        if not rows:
            return None
        rows.sort(key=lambda r: r.get("month") or "", reverse=True)
        latest = rows[0]
        prev = rows[1] if len(rows) > 1 else None
        pmi = latest.get("pmi010000")
        prev_pmi = prev.get("pmi010000") if prev else None
        if pmi is None:
            return None
        # PMI sits around 50; "trend" describes expansion vs contraction
        if pmi >= 50.5:
            phase = "扩张区间"
        elif pmi >= 49.5:
            phase = "荣枯线附近"
        else:
            phase = "收缩区间"
        delta = ""
        if prev_pmi is not None:
            delta = f"；环比 {pmi - prev_pmi:+.1f}"
        trend = f"{phase}{delta}"
        return {
            "name": "制造业 PMI",
            "value": pmi,
            "unit": "指数",
            "period": _format_month(latest.get("month")),
            "trend": trend,
        }

    async def _fetch_social_financing(self) -> dict | None:
        rows = await self._call(
            "sf_month", params={}, fields="month,inc_month,inc_cumval"
        )
        if not rows:
            return None
        rows.sort(key=lambda r: r.get("month") or "", reverse=True)
        latest = rows[0]
        return {
            "name": "社会融资规模",
            "value": latest.get("inc_month"),
            "unit": "亿元（当月新增）",
            "period": _format_month(latest.get("month")),
            "trend": f"当月新增 {latest.get('inc_month')} 亿元；累计 {latest.get('inc_cumval')} 亿元",
        }


def _format_month(yyyymm: str | None) -> str:
    if not yyyymm or len(str(yyyymm)) != 6:
        return str(yyyymm or "")
    s = str(yyyymm)
    return f"{s[:4]}-{s[4:]}"


def _describe_yoy_trend(name: str, current: float | None, prev: float | None) -> str:
    if current is None:
        return ""
    if prev is None:
        return f"{name} 同比 {current:.1f}%"
    delta = current - prev
    direction = "上升" if delta > 0.05 else "下降" if delta < -0.05 else "持平"
    return f"环比{direction} ({delta:+.1f} pp)"

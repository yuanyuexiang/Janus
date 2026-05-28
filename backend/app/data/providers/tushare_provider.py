"""Tushare Pro HTTP provider。

Tushare Pro 用单个 POST 端点的 JSON-RPC 风格协议：请求体里塞 `api_name`、
`token`、`params`、`fields` 四个字段。参考文档：https://tushare.pro/document/2

已对接的端点：
  - get_price            → daily_basic + daily       （需要申请，积分 ≥600）
  - get_macro_indicator  → cn_m / cn_ppi / cn_pmi / sf_month / cn_cpi（免费层可用）
  - search_news          → news（新浪 / 华尔街见闻等频道）

我们尝试过但默认 token 拿不到（40203 权限错误）的端点，会无感落到 MockProvider：
  - stock_basic / daily / daily_basic / cn_cpi / cn_gdp / trade_cal / index_basic / index_daily
  注：即便积分够，也需要在每个端点的文档页单独点"申请使用"。
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

# 代码归一化：600519 → 600519.SH，000001 → 000001.SZ，300750 → 300750.SZ
# A 股规则：6 开头 → SH，0/3 开头 → SZ，8/4 开头 → BJ（北交所）
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
    # 美股代码（AAPL 等）—— Tushare 不覆盖，返回 None 让链上下一个 provider 接
    return None


class TushareProvider(DataProvider):
    name = "tushare"

    # 进程内缓存：Tushare 免费层多数端点限速 1 次/小时，所以按
    # (api_name, sorted_params) 缓存 1 小时。
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
        """底层 Tushare 调用，1 小时缓存；HTTP 错误或返回 code != 0 时抛异常。"""
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
        # trust_env=False 绕过 macOS / shell 的 HTTP(S)_PROXY 设置 —— Tushare 的 IP
        # 在多数本地代理（Clash 等）的规则里不通，会卡住或被拒。我们直连。
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
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
        """单次 daily_basic 调用 —— Tushare 免费层这个端点限速 1 次/分钟，所以不
        做日期回溯。如果当前还没有最新交易日数据（周末 / 早盘），返回 None 让
        MockProvider 兜底。

        `_call` 的 1 小时缓存意味着同一标的 1 小时内重复查询是免费的。
        """
        ts_code = _normalize_ts_code(symbol)
        if not ts_code:
            return None  # not an A-share; let mock handle (e.g. AAPL)

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
            return None

        rows.sort(key=lambda r: r.get("trade_date") or "", reverse=True)
        latest = rows[0]

        # 从 daily 端点取 pct_chg（独立的 1 次/分钟配额）—— 拿到就用，拿不到也没事
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
            logger.debug("tushare daily pct_chg %s failed: %s", ts_code, e)

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
        """对接我们已申请到 Tushare 权限的指标；其它（gdp / fx 等）返回 None
        让 MockProvider 接管。
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
            if key == "cpi":
                return await self._fetch_cpi()
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
        # PMI 围绕 50 波动；trend 描述是扩张还是收缩区间
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

    async def _fetch_cpi(self) -> dict | None:
        rows = await self._call(
            "cn_cpi", params={}, fields="month,nt_yoy,nt_mom,nt_accu"
        )
        if not rows:
            return None
        rows.sort(key=lambda r: r.get("month") or "", reverse=True)
        latest = rows[0]
        prev = rows[1] if len(rows) > 1 else None
        yoy = latest.get("nt_yoy")
        trend = _describe_yoy_trend("CPI", yoy, prev.get("nt_yoy") if prev else None)
        return {
            "name": "CPI 同比",
            "value": yoy,
            "unit": "%",
            "period": _format_month(latest.get("month")),
            "trend": trend,
            "detail": {"nt_mom": latest.get("nt_mom"), "nt_accu": latest.get("nt_accu")},
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


    # ---------- News ----------

    async def search_news(
        self,
        query: str | None = None,
        limit: int = 20,
    ) -> dict | None:
        """从 Tushare `news` 端点拉最近新闻（默认新浪源）。

        Tushare `news` 不支持服务端关键词过滤，所以一次拉一批回来再本地
        substring 过滤。共享 `_call` 缓存（按小时对齐窗口，命中率高）。
        """
        # 只用日期粒度的窗口（Tushare news 端点对格式挑剔）。
        # 把当前时间向下取整到 1 小时，让缓存 key 按小时分组。
        from datetime import datetime, timedelta

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        start = (now - timedelta(days=2)).strftime("%Y-%m-%d")
        end = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            rows = await self._call(
                "news",
                params={"src": "sina", "start_date": start, "end_date": end},
                fields="datetime,content,title,channels",
            )
        except Exception as e:
            logger.warning("tushare news failed: %s", e)
            return None
        if not rows:
            return None

        # 按 title 去重（新浪有时不带 title —— 用 content 前 60 字符代替）。
        # 新浪新闻不是关键词索引，窗口窄时 substring 命中可能为 0；这种情况
        # 退化为返回最新条目，避免顾问拿不到任何上下文。
        seen: set[str] = set()
        deduped: list[dict] = []
        for r in rows:
            content = (r.get("content") or "").strip()
            title = (r.get("title") or "").strip()
            if not title:
                # 回退：取 content 的第一行作为 title
                snippet = content.split("\n", 1)[0].strip()
                title = snippet[:60] + ("…" if len(snippet) > 60 else "")
            if not title or title in seen:
                continue
            seen.add(title)
            deduped.append(
                {
                    "datetime": r.get("datetime"),
                    "title": title,
                    "content": content[:240],
                    "channel": r.get("channels"),
                }
            )

        cap = max(1, min(limit, 50))
        q = (query or "").strip()
        matched: list[dict] = []
        if q:
            for item in deduped:
                if q in item["title"] or q in (item["content"] or ""):
                    matched.append(item)
                    if len(matched) >= cap:
                        break

        if not matched:
            # 没传 query，或者 query 没命中 —— 给顾问最新条目托底
            matched = deduped[:cap]
            fallback = bool(q)
        else:
            fallback = False

        matched.sort(key=lambda x: x.get("datetime") or "", reverse=True)
        result: dict = {
            "query": q or None,
            "count": len(matched),
            "items": matched,
        }
        if fallback:
            result["note"] = f"query '{q}' had 0 substring matches in the recent window; returning latest headlines instead"
        return result


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

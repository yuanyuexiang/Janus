"""ChoiceProvider —— 东方财富 Choice 数据 provider，**走 HTTP 调 choice-gateway**。

设计原则（Plan C）：
- backend 不直接依赖 EmQuantAPI SDK
- SDK + 登录态 + 设备配额 都在独立的 choice-gateway 服务里
- 这里只做 HTTP 客户端 + 把 gateway 的响应映射成 DataProvider 标准形状
- gateway 连不上 / SDK 未就绪 / 网关返回错误时，统一**返回 None**
  让 DataSource 自动落到下一个 provider（Tushare / Mock）—— 永远不抛
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.data.providers.base import DataProvider

logger = logging.getLogger(__name__)


class ChoiceProvider(DataProvider):
    name = "choice"

    def __init__(self, gateway_url: str, timeout: float = 8.0) -> None:
        self.base_url = gateway_url.rstrip("/")
        self.timeout = timeout

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict | None:
        """通用 GET。返回 None 让上层 fall through。"""
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                r = await client.get(url, params=params)
        except Exception as e:
            logger.warning("choice-gateway 不可达 %s: %s", path, e)
            return None
        if r.status_code == 503:
            # SDK 未就绪（未激活 / 未登录），不告警，让 DataSource 静默落下一层
            return None
        if r.status_code >= 400:
            logger.warning("choice-gateway %s 返回 %s: %s", path, r.status_code, r.text[:200])
            return None
        try:
            body = r.json()
        except Exception:
            logger.warning("choice-gateway %s 响应不是 JSON", path)
            return None
        if not body.get("ok"):
            # 业务错误（UNKNOWN_INDICATOR 等）—— 不告警，落下一层
            return None
        return body.get("data")

    # ---------- 接口实现 ----------

    async def get_price(self, symbol: str) -> dict | None:
        return await self._get("/api/price", {"symbol": symbol})

    async def get_kline(self, symbol: str, days: int = 30) -> dict | None:
        return await self._get("/api/kline", {"symbol": symbol, "days": days})

    async def get_macro_indicator(self, indicator: str) -> dict | None:
        return await self._get("/api/macro", {"indicator": indicator})

    async def get_industry_overview(self, industry: str) -> dict | None:
        return await self._get("/api/industry", {"industry": industry})

    async def search_news(self, query: str | None = None, limit: int = 20) -> dict | None:
        return await self._get(
            "/api/news",
            {"query": query or "", "limit": limit},
        )

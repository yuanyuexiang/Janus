"""DataProvider 基类。子类只覆盖自己支持的方法，其余返回 None；
DataSource 会依次走完 provider 链，用第一个非 None 的返回值。"""

from __future__ import annotations

from abc import ABC


class DataProvider(ABC):
    name: str = "base"

    async def get_price(self, symbol: str) -> dict | None:
        """返回行情快照 `{symbol, name, price, change_pct, pe, ...}`；
        如果本 provider 处理不了，返回 None。"""
        return None

    async def get_macro_indicator(self, indicator: str) -> dict | None:
        """返回宏观指标的最新读数
        （如 cpi / m2 / pmi_manufacturing / interest_rate_10y 等）。"""
        return None

    async def get_industry_overview(self, industry: str) -> dict | None:
        """返回行业概览：名称、代码、近期表现、平均 PE、龙头成分股等。"""
        return None

    async def get_kline(self, symbol: str, days: int = 30) -> dict | None:
        """返回标的的日 K 线。
        形状：{symbol, name, bars: [{date, open, high, low, close, volume, pct_chg}, ...]}"""
        return None

    async def search_news(
        self,
        query: str | None = None,
        limit: int = 20,
    ) -> dict | None:
        """搜索最近的新闻条目。

        参数：
          query: 关键词过滤（在 title / content 中做子串匹配）；为 None 时返回最新条目。
          limit: 返回条目数上限（1-50）。

        返回：{query, count, items: [{datetime, title, content?, channel?}, ...]}，
        最新条目排在前面。
        """
        return None

"""DataSource —— 多 provider 编排器，带优雅回退。

provider 链优先级（从高到低）：
  1. ChoiceProvider  —— 当配置了 CHOICE_GATEWAY_URL 时启用（走 HTTP 调独立 gateway 服务）
  2. TushareProvider —— 当配置了 TUSHARE_TOKEN 时启用
  3. MockProvider    —— 永远存在，作为最终兜底

每个方法依次走完链上的 provider，遇到第一个非 None 的返回值就用它；
如果所有 provider 都没数据，返回结构化的错误信封（DataEnvelope.error）。
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings
from app.data.providers.base import DataProvider
from app.data.providers.mock import MockProvider
from app.data.types import DataEnvelope, err, ok

logger = logging.getLogger(__name__)


def _build_chain() -> list[DataProvider]:
    settings = get_settings()
    chain: list[DataProvider] = []
    if settings.choice_gateway_url:
        try:
            from app.data.providers.choice_provider import ChoiceProvider

            chain.append(ChoiceProvider(gateway_url=settings.choice_gateway_url))
            logger.info("DataSource: 已启用 ChoiceProvider (gateway=%s)", settings.choice_gateway_url)
        except Exception:
            logger.exception("DataSource: ChoiceProvider 初始化失败，跳过")
    if settings.tushare_token:
        try:
            from app.data.providers.tushare_provider import TushareProvider

            chain.append(TushareProvider(token=settings.tushare_token))
            logger.info("DataSource: 已启用 TushareProvider")
        except Exception:
            logger.exception("DataSource: TushareProvider 初始化失败，跳过")
    chain.append(MockProvider())
    return chain


class DataSource:
    def __init__(self, providers: list[DataProvider] | None = None) -> None:
        self.providers = providers if providers is not None else _build_chain()

    def provider_names(self) -> list[str]:
        return [p.name for p in self.providers]

    async def get_price(self, symbol: str) -> DataEnvelope:
        for p in self.providers:
            try:
                result = await p.get_price(symbol)
            except Exception as e:
                logger.warning("provider %s get_price 失败: %s", p.name, e)
                continue
            if result is not None:
                return ok(result, source=p.name)
        return err("SYMBOL_NOT_FOUND", f"未知标的：{symbol}")

    async def get_macro_indicator(self, indicator: str) -> DataEnvelope:
        for p in self.providers:
            try:
                result = await p.get_macro_indicator(indicator)
            except Exception as e:
                logger.warning("provider %s get_macro_indicator 失败: %s", p.name, e)
                continue
            if result is not None:
                return ok(result, source=p.name)
        return err("INDICATOR_NOT_FOUND", f"未知宏观指标：{indicator}")

    async def get_industry_overview(self, industry: str) -> DataEnvelope:
        for p in self.providers:
            try:
                result = await p.get_industry_overview(industry)
            except Exception as e:
                logger.warning("provider %s get_industry_overview 失败: %s", p.name, e)
                continue
            if result is not None:
                return ok(result, source=p.name)
        return err("INDUSTRY_NOT_FOUND", f"未知行业：{industry}")

    async def get_kline(self, symbol: str, days: int = 30) -> DataEnvelope:
        for p in self.providers:
            try:
                result = await p.get_kline(symbol, days)
            except Exception as e:
                logger.warning("provider %s get_kline 失败: %s", p.name, e)
                continue
            if result is not None:
                return ok(result, source=p.name)
        return err("SYMBOL_NOT_FOUND", f"未知标的：{symbol}")

    async def search_news(
        self, query: str | None = None, limit: int = 20
    ) -> DataEnvelope:
        for p in self.providers:
            try:
                result = await p.search_news(query, limit)
            except Exception as e:
                logger.warning("provider %s search_news 失败: %s", p.name, e)
                continue
            if result is not None:
                return ok(result, source=p.name)
        return err("NEWS_UNAVAILABLE", "新闻源暂不可用")


@lru_cache
def get_data_source() -> DataSource:
    return DataSource()

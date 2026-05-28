"""DataSource — multi-provider orchestrator with graceful fallback.

Chain order (highest priority first):
  1. TushareProvider — if TUSHARE_TOKEN configured
  2. MockProvider    — always present, final fallback

Each method walks the chain and returns the first non-None response, or a
structured error envelope if all providers came up empty.
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
    if settings.tushare_token:
        try:
            from app.data.providers.tushare_provider import TushareProvider

            chain.append(TushareProvider(token=settings.tushare_token))
            logger.info("DataSource: TushareProvider enabled")
        except Exception:
            logger.exception("DataSource: failed to init TushareProvider; skipping")
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
                logger.warning("provider %s get_price failed: %s", p.name, e)
                continue
            if result is not None:
                return ok(result, source=p.name)
        return err("SYMBOL_NOT_FOUND", f"未知标的：{symbol}")

    async def get_macro_indicator(self, indicator: str) -> DataEnvelope:
        for p in self.providers:
            try:
                result = await p.get_macro_indicator(indicator)
            except Exception as e:
                logger.warning("provider %s get_macro_indicator failed: %s", p.name, e)
                continue
            if result is not None:
                return ok(result, source=p.name)
        return err("INDICATOR_NOT_FOUND", f"未知宏观指标：{indicator}")

    async def get_industry_overview(self, industry: str) -> DataEnvelope:
        for p in self.providers:
            try:
                result = await p.get_industry_overview(industry)
            except Exception as e:
                logger.warning("provider %s get_industry_overview failed: %s", p.name, e)
                continue
            if result is not None:
                return ok(result, source=p.name)
        return err("INDUSTRY_NOT_FOUND", f"未知行业：{industry}")

    async def get_kline(self, symbol: str, days: int = 30) -> DataEnvelope:
        for p in self.providers:
            try:
                result = await p.get_kline(symbol, days)
            except Exception as e:
                logger.warning("provider %s get_kline failed: %s", p.name, e)
                continue
            if result is not None:
                return ok(result, source=p.name)
        return err("SYMBOL_NOT_FOUND", f"未知标的：{symbol}")


@lru_cache
def get_data_source() -> DataSource:
    return DataSource()

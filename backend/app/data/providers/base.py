"""DataProvider base class. Providers override the methods they support and return
None for the rest; DataSource walks the provider chain and uses the first non-None."""

from __future__ import annotations

from abc import ABC


class DataProvider(ABC):
    name: str = "base"

    async def get_price(self, symbol: str) -> dict | None:
        """Return a price snapshot `{symbol, name, price, change_pct, pe, ...}`
        or None if this provider can't serve the request."""
        return None

    async def get_macro_indicator(self, indicator: str) -> dict | None:
        """Return latest reading for a macro indicator
        (e.g. cpi / m2 / pmi_manufacturing / interest_rate_10y)."""
        return None

    async def get_industry_overview(self, industry: str) -> dict | None:
        """Return a basic overview for an industry: name, code, latest movers,
        average PE, top constituents, etc."""
        return None

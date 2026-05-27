"""Mock market data for M1/M2. M3 replaces this with Choice/Tushare providers.

`get_price` is exposed as the `market_get_price` MCP tool by app.mcp_servers.market.
"""

from datetime import datetime, timezone

MOCK_DB: dict[str, dict] = {
    "600519.SH": {"name": "贵州茅台", "price": 1820.50, "change_pct": -1.23, "pe": 28.4},
    "300750.SZ": {"name": "宁德时代", "price": 245.30, "change_pct": -2.10, "pe": 18.7},
    "000001.SZ": {"name": "平安银行", "price": 11.85, "change_pct": 0.51, "pe": 5.2},
    "AAPL": {"name": "Apple", "price": 187.42, "change_pct": 0.83, "pe": 31.2},
}


async def get_price(symbol: str) -> dict:
    sym = symbol.upper().strip()
    row = MOCK_DB.get(sym)
    now = datetime.now(timezone.utc).isoformat()
    if not row:
        return {
            "ok": False,
            "data": None,
            "source": None,
            "as_of": now,
            "error": {"code": "SYMBOL_NOT_FOUND", "message": f"未知标的：{symbol}"},
        }
    return {
        "ok": True,
        "data": {
            "symbol": sym,
            "name": row["name"],
            "price": row["price"],
            "change_pct": row["change_pct"],
            "pe": row["pe"],
        },
        "source": "mock",
        "as_of": now,
        "error": None,
    }

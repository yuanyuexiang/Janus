"""Market data MCP server.

Backed by the DataSource chain (TushareProvider when token configured →
MockProvider fallback). Speaks MCP over stdio.

Run as: `python -m app.mcp_servers.market`
"""

from mcp.server.fastmcp import FastMCP

from app.data.datasource import get_data_source

mcp = FastMCP("market")


@mcp.tool()
async def market_get_price(symbol: str) -> dict:
    """Get the latest price snapshot for a stock symbol.

    Symbols accept both raw (`600519`) and qualified (`600519.SH`) forms for
    A-shares; bare tickers for US (`AAPL`, `MSFT`, `NVDA`). Returns:

      - `symbol` (normalized), `name`, `price` (close), `change_pct`, `pe`
      - When the data comes from Tushare: also `pb`, `trade_date`,
        `turnover_rate`, `circ_mv`
      - envelope `source` field tells which provider answered (`tushare` / `mock`)

    Always check `ok` before reading `data`. When `ok=false`, do **not**
    invent figures; report the data gap instead.
    """
    ds = get_data_source()
    return await ds.get_price(symbol)


@mcp.tool()
async def market_get_kline(symbol: str, days: int = 30) -> dict:
    """Get daily OHLCV K-line bars for a symbol.

    Args:
      - `symbol`: e.g. `600519`, `600519.SH`, `AAPL`. Raw 6-digit A-share codes
        are auto-suffixed (.SH/.SZ/.BJ).
      - `days`: number of bars (5-120, default 30).

    Returns the bars (oldest first) plus a summary block (range_high, range_low,
    range_pct_chg over the window, avg_volume). When `source=mock`, the series
    is a deterministic pseudo random walk seeded by symbol — not real market
    data; explicitly warn the user when relying on it.
    """
    ds = get_data_source()
    return await ds.get_kline(symbol, days)


if __name__ == "__main__":
    mcp.run()

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
      - `_source` field of the envelope tells which provider answered
        (`tushare` or `mock`)

    Always check `ok` before reading `data`. When `ok=false`, do **not**
    invent figures; report the data gap instead.
    """
    ds = get_data_source()
    return await ds.get_price(symbol)


if __name__ == "__main__":
    mcp.run()

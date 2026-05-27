"""Market data MCP server.

Run as: `python -m app.mcp_servers.market`. Speaks MCP over stdio.
For M1/M2 the underlying data is the mock table in app.tools.market;
M3 swaps this for Choice/Tushare providers transparently.
"""

from mcp.server.fastmcp import FastMCP

from app.tools.market import get_price

mcp = FastMCP("market")


@mcp.tool()
async def market_get_price(symbol: str) -> dict:
    """Get the latest price snapshot for a stock symbol.

    Symbols use exchange suffixes for A-shares (e.g. 600519.SH, 300750.SZ)
    or bare tickers for US (e.g. AAPL). Returns a dict with `ok`, `data`,
    `source`, `as_of`, `error`. Always check `ok` before reading `data`.
    """
    return await get_price(symbol)


if __name__ == "__main__":
    mcp.run()

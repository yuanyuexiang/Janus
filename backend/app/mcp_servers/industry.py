"""Industry overview MCP server.

Exposes `industry_get_overview(industry)`. M3 v1 backed by MockProvider's
curated industry table (8 sectors). M3.1 swaps in Tushare `index_basic` +
`index_daily` for live sector indices.

Run as: `python -m app.mcp_servers.industry`
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.data.datasource import get_data_source
from app.data.providers.mock import known_industries

mcp = FastMCP("industry")


@mcp.tool()
async def industry_get_overview(industry: str) -> dict:
    """Get a structured overview of a Chinese A-share industry.

    Accepts canonical names (白酒 / 锂电池 / 银行 / 半导体 / 创新药 / 证券 /
    新能源汽车 / 公用事业) or common aliases (动力电池 → 锂电池, 电动车 →
    新能源汽车, 芯片 → 半导体, etc.).

    Returns: name, average P/E, YTD return, top constituents, narrative trend,
    and key drivers to watch. Always check `ok` before reading `data`.
    """
    ds = get_data_source()
    return await ds.get_industry_overview(industry)


@mcp.tool()
async def industry_list() -> dict[str, Any]:
    """List every industry name that `industry_get_overview` recognises."""
    return {
        "ok": True,
        "data": {"industries": known_industries()},
        "source": "registry",
        "error": None,
    }


if __name__ == "__main__":
    mcp.run()

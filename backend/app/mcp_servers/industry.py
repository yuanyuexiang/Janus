"""行业概览 MCP server。

暴露 `industry_get_overview(industry)`。M3 v1 走 MockProvider 的预置行业表
（8 个板块）。M3.1 起对接 Tushare `index_basic` + `index_daily` 拉真实行业指数。

运行方式：`python -m app.mcp_servers.industry`
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.data.datasource import get_data_source
from app.data.providers.mock import known_industries

mcp = FastMCP("industry")


@mcp.tool()
async def industry_get_overview(industry: str) -> dict:
    """取一个 A 股行业的结构化概览。

    接受标准行业名（白酒 / 锂电池 / 银行 / 半导体 / 创新药 / 证券 /
    新能源汽车 / 公用事业），也接受常用别名（动力电池 → 锂电池，
    电动车 → 新能源汽车，芯片 → 半导体 等等）。

    返回：name、平均 PE、年初至今涨跌幅、龙头成分股、趋势描述、关键观察因子。
    使用 `data` 前请先检查 `ok`。
    """
    ds = get_data_source()
    return await ds.get_industry_overview(industry)


@mcp.tool()
async def industry_list() -> dict[str, Any]:
    """列出 `industry_get_overview` 支持的所有行业名。"""
    return {
        "ok": True,
        "data": {"industries": known_industries()},
        "source": "registry",
        "error": None,
    }


if __name__ == "__main__":
    mcp.run()

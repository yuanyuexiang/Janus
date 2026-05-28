"""宏观指标 MCP server。

暴露 `macro_get_indicators(name)`。M3 v1 主要走 MockProvider 的预置指标
集合；M3.1 接通后 Tushare 的 `cn_cpi / cn_ppi / cn_m / cn_pmi / sf_month`
经 TushareProvider 自动接管，顾问代码无感知。

运行方式：`python -m app.mcp_servers.macro`
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.data.datasource import get_data_source
from app.data.providers.mock import known_macro_indicators

mcp = FastMCP("macro")


@mcp.tool()
async def macro_get_indicators(indicator: str) -> dict:
    """取一个宏观指标的最新读数。

    支持的指标名（精确匹配）：
      - `cpi` —— CPI 同比
      - `ppi` —— PPI 同比
      - `m2` —— M2 货币供应同比
      - `pmi_manufacturing` —— 制造业 PMI
      - `pmi_non_manufacturing` —— 非制造业 PMI（服务业 + 建筑业）
      - `interest_rate_10y` —— 10 年期国债收益率
      - `us_fed_funds_rate` —— 美联储基金利率上限
      - `usd_cny` —— 美元兑人民币
      - `social_financing` —— 社会融资规模存量同比

    返回最新读数：`value`、`unit`、`period`，附一段简短 `trend` 趋势描述。
    使用 `data` 前请先检查 `ok`。
    """
    ds = get_data_source()
    return await ds.get_macro_indicator(indicator)


@mcp.tool()
async def macro_list_indicators() -> dict[str, Any]:
    """列出 `macro_get_indicators` 支持的所有指标名。"""
    return {
        "ok": True,
        "data": {"indicators": known_macro_indicators()},
        "source": "registry",
        "error": None,
    }


if __name__ == "__main__":
    mcp.run()

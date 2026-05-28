"""Macro indicators MCP server.

Exposes `macro_get_indicators(name)`. M3 v1 backed by MockProvider with a
curated set of indicators; M3.1 wires Tushare's `cn_cpi`, `cn_ppi`, `cn_m`,
`cn_pmi` endpoints via TushareProvider transparently — no Agent code changes.

Run as: `python -m app.mcp_servers.macro`
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.data.datasource import get_data_source
from app.data.providers.mock import known_macro_indicators

mcp = FastMCP("macro")


@mcp.tool()
async def macro_get_indicators(indicator: str) -> dict:
    """Get the latest reading for a macro indicator.

    Available indicators (use these names exactly):
      - `cpi` - CPI 同比 (consumer price index, YoY)
      - `ppi` - PPI 同比 (producer price index, YoY)
      - `m2` - M2 货币供应同比
      - `pmi_manufacturing` - 制造业 PMI (manufacturing)
      - `pmi_non_manufacturing` - 非制造业 PMI (services + construction)
      - `interest_rate_10y` - 10 年期国债收益率
      - `us_fed_funds_rate` - 美联储基金利率上限
      - `usd_cny` - 美元兑人民币汇率
      - `social_financing` - 社会融资规模存量同比

    Returns the latest reading with `value`, `unit`, `period`, and a short
    `trend` description. Always check `ok` before reading `data`.
    """
    ds = get_data_source()
    return await ds.get_macro_indicator(indicator)


@mcp.tool()
async def macro_list_indicators() -> dict[str, Any]:
    """List every macro indicator name that `macro_get_indicators` accepts."""
    return {
        "ok": True,
        "data": {"indicators": known_macro_indicators()},
        "source": "registry",
        "error": None,
    }


if __name__ == "__main__":
    mcp.run()

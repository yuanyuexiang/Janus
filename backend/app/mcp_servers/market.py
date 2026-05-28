"""行情数据 MCP server。

底层走 DataSource 链（配了 TUSHARE_TOKEN 时优先 TushareProvider，
否则落到 MockProvider）。通过 stdio 协议被 backend 进程拉起。

运行方式：`python -m app.mcp_servers.market`
"""

from mcp.server.fastmcp import FastMCP

from app.data.datasource import get_data_source

mcp = FastMCP("market")


@mcp.tool()
async def market_get_price(symbol: str) -> dict:
    """取标的的最新行情快照。

    Symbol 同时接受裸代码（`600519`）和带后缀的标准形式（`600519.SH`）；
    美股用裸 ticker（`AAPL`、`MSFT`、`NVDA`）。返回：

      - `symbol`（归一化后）、`name`、`price`（收盘）、`change_pct`、`pe`
      - 数据来自 Tushare 时还附带：`pb`、`trade_date`、`turnover_rate`、`circ_mv`
      - 信封的 `source` 字段标识来源（`tushare` / `mock`）

    使用 `data` 前请先检查 `ok`。`ok=false` 时**不要**编造数字，明确告诉用户数据缺失。
    """
    ds = get_data_source()
    return await ds.get_price(symbol)


@mcp.tool()
async def market_get_kline(symbol: str, days: int = 30) -> dict:
    """取标的的日 K 线 OHLCV 数据。

    参数：
      - `symbol`：例如 `600519`、`600519.SH`、`AAPL`。裸 6 位 A 股代码会自动
        补后缀（.SH/.SZ/.BJ）。
      - `days`：返回多少根（5-120，默认 30）。

    返回 bars（按日期升序）加一份 summary（区间最高 / 最低 / 区间涨跌幅 /
    平均成交量）。当 `source=mock` 时数据是 symbol 种子的伪随机游走 ——
    **不是真实行情**，使用时务必告诉用户。
    """
    ds = get_data_source()
    return await ds.get_kline(symbol, days)


if __name__ == "__main__":
    mcp.run()

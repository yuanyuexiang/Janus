"""新闻 MCP server。

暴露 `news_search(query, limit)`，底层走 DataSource。Tushare `news` 端点
可访问时（免费层就能调）拉真实新闻；否则回退到 MockProvider 的预置新闻样本。

运行方式：`python -m app.mcp_servers.news`
"""

from mcp.server.fastmcp import FastMCP

from app.data.datasource import get_data_source

mcp = FastMCP("news")


@mcp.tool()
async def news_search(query: str = "", limit: int = 15) -> dict:
    """搜索近期财经新闻（Tushare 数据源走 48 小时滚动窗口）。

    参数：
      - `query`：关键词过滤，在 title + content 前 240 字符 + 频道名里做子串
        匹配。传空字符串拿最新头条。例：`茅台` / `锂电池` / `美联储` / `半导体`。
      - `limit`：返回数量上限，1-50（默认 15）。新条目排在前面。

    返回：`{query, count, items: [{datetime, title, content, channel}]}`。

    当 `source=mock` 时返回的是预置样本（不是实时新闻），向用户输出时务必标明。
    """
    ds = get_data_source()
    return await ds.search_news(query or None, limit)


if __name__ == "__main__":
    mcp.run()

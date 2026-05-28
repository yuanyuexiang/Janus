"""Tushare 端点权限探针：当前 token 能访问哪些接口。

Tushare 免费层按积分门控（默认 100，验邮箱 + 绑手机后最高 5000）。
本脚本挑了价格 / 基本面 / 宏观 / 行业 / K 线几类代表端点，分别试一下
哪些能拿到数据、哪些会 401 / 40203 权限不足。
"""

import asyncio
import json

import httpx

from app.config import get_settings

URL = "https://api.tushare.pro"


async def call(api_name: str, params: dict, fields: str = "", token: str = ""):
    payload = {"api_name": api_name, "token": token, "params": params, "fields": fields}
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.post(URL, json=payload)
    return r.status_code, r.json()


async def try_endpoint(name: str, params: dict, fields: str, token: str) -> str:
    try:
        status, body = await call(name, params, fields, token)
    except Exception as e:
        return f"  ✗ {name:25s} ERR  {type(e).__name__}: {str(e)[:80]}"
    code = body.get("code")
    if code != 0:
        msg = (body.get("msg") or "").strip()
        return f"  ✗ {name:25s} code={code}  msg={msg[:120]}"
    items = (body.get("data") or {}).get("items") or []
    cols = (body.get("data") or {}).get("fields") or []
    sample = ""
    if items:
        sample = " | ".join(f"{c}={v}" for c, v in zip(cols, items[0]))
    return f"  ✓ {name:25s} rows={len(items):>4}  sample: {sample[:120]}"


async def main() -> None:
    token = get_settings().tushare_token
    if not token:
        raise SystemExit(".env 里没配 TUSHARE_TOKEN")

    probes = [
        # === 股票元数据 / 基本行情 ===
        ("stock_basic",  {"ts_code": "600519.SH"}, "ts_code,name,industry"),
        ("daily",        {"ts_code": "600519.SH", "limit": 5}, "ts_code,trade_date,close,pct_chg"),
        ("daily_basic",  {"ts_code": "600519.SH", "limit": 3}, "ts_code,trade_date,close,pe,pb"),

        # === 宏观指标 ===
        ("cn_cpi",       {}, "month,nt_yoy"),
        ("cn_ppi",       {}, "month,ppi_yoy"),
        ("cn_m",         {}, "month,m2_yoy,m1_yoy,m0_yoy"),
        ("cn_pmi",       {}, "month,pmi010000"),
        ("cn_sf",        {}, "month,inc_month"),

        # === 行业指数 ===
        ("index_basic",  {"market": "SW"}, "ts_code,name,fullname"),
        ("index_daily",  {"ts_code": "801080.SI", "limit": 3}, "ts_code,trade_date,close,pct_chg"),  # 申万电子
    ]

    print(f"Token: {token[:8]}...{token[-6:]}\n")
    results = await asyncio.gather(*(try_endpoint(*p, token) for p in probes))
    for r in results:
        print(r)


if __name__ == "__main__":
    asyncio.run(main())

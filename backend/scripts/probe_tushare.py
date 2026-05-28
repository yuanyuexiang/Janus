"""Probe which Tushare endpoints our token can access.

Tushare's free tier gates endpoints behind point scores (100 default, up to
5000 after email + phone verify). This script tries representative endpoints
across price / fundamentals / macro / industry / kline categories and reports
which ones return data vs which 401 due to insufficient points.
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
        raise SystemExit("TUSHARE_TOKEN not set in .env")

    probes = [
        # === Stock metadata / basic price ===
        ("stock_basic",  {"ts_code": "600519.SH"}, "ts_code,name,industry"),
        ("daily",        {"ts_code": "600519.SH", "limit": 5}, "ts_code,trade_date,close,pct_chg"),
        ("daily_basic",  {"ts_code": "600519.SH", "limit": 3}, "ts_code,trade_date,close,pe,pb"),

        # === Macro indicators ===
        ("cn_cpi",       {}, "month,nt_yoy"),
        ("cn_ppi",       {}, "month,ppi_yoy"),
        ("cn_m",         {}, "month,m2_yoy,m1_yoy,m0_yoy"),
        ("cn_pmi",       {}, "month,pmi010000"),
        ("cn_sf",        {}, "month,inc_month"),

        # === Industry indices ===
        ("index_basic",  {"market": "SW"}, "ts_code,name,fullname"),
        ("index_daily",  {"ts_code": "801080.SI", "limit": 3}, "ts_code,trade_date,close,pct_chg"),  # SW 电子
    ]

    print(f"Token: {token[:8]}...{token[-6:]}\n")
    results = await asyncio.gather(*(try_endpoint(*p, token) for p in probes))
    for r in results:
        print(r)


if __name__ == "__main__":
    asyncio.run(main())

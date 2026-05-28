"""Choice Gateway HTTP 服务入口。

只 backend 内网可访问；不做鉴权（信任 docker-compose 网络隔离）。

路由：
  GET  /healthz               健康检查 + SDK 状态
  POST /api/activate?phone=…  短信激活（一次性）
  GET  /api/price?symbol=…    最新行情快照
  GET  /api/kline?symbol=…&days=30   日 K 线
  GET  /api/macro?indicator=… 宏观指标最新读数
  GET  /api/industry?industry=…  行业指数概览
  GET  /api/news?query=&limit=15 新闻搜索
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from app import sdk
from app.config import get_settings
from app.envelope import err, ok
from app.mappers import lookup_industry, lookup_macro, normalize_symbol

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Choice Gateway 启动，SDK 路径 = %s", settings.sdk_path)
    # 启动时尝试用已有 userInfo 自动登录；没令牌也不报错
    sdk.try_auto_login()
    yield
    sdk.shutdown()
    logger.info("Choice Gateway 已退出")


app = FastAPI(title="Choice Gateway", lifespan=lifespan)


# ---------- 健康检查 ----------


@app.get("/healthz")
async def healthz() -> dict:
    s = sdk.get_status()
    return {
        "service": "choice-gateway",
        "sdk_available": s.available,
        "sdk_logged_in": s.logged_in,
        "last_error": s.last_error,
    }


# ---------- 激活 ----------


@app.post("/api/activate")
async def activate(phone: str = Query(..., description="绑定到 Choice 账号的手机号")) -> JSONResponse:
    """触发上行短信激活。
    前置：在 10 分钟内用该手机号发短信 SXDL 到 9535711。
    成功后 SDK 会写 userInfo 令牌，后续重启自动登录。"""
    ok_login, msg = sdk.activate_sms(phone)
    if ok_login:
        return JSONResponse({"ok": True, "message": "已激活并生成 userInfo"})
    return JSONResponse({"ok": False, "message": msg}, status_code=400)


# ---------- 业务 ----------


def _require_sdk() -> tuple | None:
    """SDK 未就绪时统一返回 503。"""
    s = sdk.get_status()
    if not s.logged_in:
        env, code = err("SDK_NOT_READY", s.last_error or "Choice SDK 未登录", 503)
        return JSONResponse(env, status_code=code)
    return None


@app.get("/api/price")
async def get_price(symbol: str = Query(..., description="标的代码，例 600519.SH / AAPL")) -> JSONResponse:
    fail = _require_sdk()
    if fail:
        return fail
    sym = normalize_symbol(symbol)
    try:
        # 截面：股票名 + 现价 + 涨跌幅 + PE_TTM + PB
        result = await sdk.call(
            "css",
            sym,
            "NAME,NOW,CHGPCT,PETTM,PBMRQ,VOLUME,AMOUNT",
        )
    except Exception as e:
        env, code = err("CHOICE_CALL_FAILED", str(e), 200)
        return JSONResponse(env)
    if sym not in result.Codes:
        env, code = err("NO_DATA", f"Choice 未返回 {sym} 的数据", 200)
        return JSONResponse(env)
    row = result.Data[sym]
    inds = result.Indicators
    val = dict(zip(inds, row))
    payload = {
        "symbol": sym,
        "name": val.get("NAME"),
        "price": val.get("NOW"),
        "change_pct": val.get("CHGPCT"),
        "pe": val.get("PETTM"),
        "pb": val.get("PBMRQ"),
        "volume": val.get("VOLUME"),
        "amount": val.get("AMOUNT"),
    }
    return JSONResponse(ok(payload))


@app.get("/api/kline")
async def get_kline(
    symbol: str = Query(...),
    days: int = Query(30, ge=5, le=120),
) -> JSONResponse:
    fail = _require_sdk()
    if fail:
        return fail
    sym = normalize_symbol(symbol)
    from datetime import datetime, timedelta

    end_d = datetime.utcnow().date()
    start_d = end_d - timedelta(days=int(days * 1.6))  # 留些余量给非交易日
    try:
        result = await sdk.call(
            "csd",
            sym,
            "OPEN,HIGH,LOW,CLOSE,VOLUME,AMOUNT",
            start_d.strftime("%Y-%m-%d"),
            end_d.strftime("%Y-%m-%d"),
            "Period=1,AdjustFlag=1",
        )
    except Exception as e:
        env, _ = err("CHOICE_CALL_FAILED", str(e))
        return JSONResponse(env)
    if sym not in result.Codes:
        env, _ = err("NO_DATA", f"Choice 未返回 {sym} 的 K 线", 200)
        return JSONResponse(env)
    inds = result.Indicators
    dates = result.Dates
    raw = result.Data[sym]
    bars = []
    for j, d in enumerate(dates):
        bar = {"date": str(d)}
        for i, ind in enumerate(inds):
            v = raw[i][j]
            bar[ind.lower()] = v
        bars.append(bar)
    # 仅取最后 `days` 根
    bars = bars[-days:]
    if bars:
        first_close = bars[0].get("close")
        last_close = bars[-1].get("close")
        range_pct = (
            (last_close - first_close) / first_close * 100
            if first_close
            else None
        )
        summary = {
            "range_high": max(b.get("high") for b in bars if b.get("high") is not None),
            "range_low": min(b.get("low") for b in bars if b.get("low") is not None),
            "range_pct_chg": round(range_pct, 2) if range_pct is not None else None,
            "avg_volume": sum(b.get("volume") or 0 for b in bars) // max(len(bars), 1),
        }
    else:
        summary = None
    return JSONResponse(ok({"symbol": sym, "days": len(bars), "summary": summary, "bars": bars}))


@app.get("/api/macro")
async def get_macro(indicator: str = Query(...)) -> JSONResponse:
    fail = _require_sdk()
    if fail:
        return fail
    meta = lookup_macro(indicator)
    if not meta:
        env, _ = err("UNKNOWN_INDICATOR", f"没有 EDB 映射：{indicator}", 200)
        return JSONResponse(env)
    try:
        result = await sdk.call(
            "edb",
            meta["id"],
            "RowIndex=1,IsLatest=1",
        )
    except Exception as e:
        env, _ = err("CHOICE_CALL_FAILED", str(e))
        return JSONResponse(env)
    if not result.Codes:
        env, _ = err("NO_DATA", f"EDB {meta['id']} 无数据", 200)
        return JSONResponse(env)
    code = result.Codes[0]
    vals = result.Data.get(code) or []
    dates = list(result.Dates)
    latest_val = vals[-1] if vals else None
    latest_date = dates[-1] if dates else None
    return JSONResponse(
        ok(
            {
                "name": meta["name"],
                "value": latest_val,
                "unit": meta["unit"],
                "period": str(latest_date) if latest_date else None,
                "edb_id": meta["id"],
            }
        )
    )


@app.get("/api/industry")
async def get_industry(industry: str = Query(...)) -> JSONResponse:
    fail = _require_sdk()
    if fail:
        return fail
    meta = lookup_industry(industry)
    if not meta:
        env, _ = err("UNKNOWN_INDUSTRY", f"没有指数映射：{industry}", 200)
        return JSONResponse(env)
    try:
        # 截面取行业指数：名称 + 现价 + 当日涨跌 + 年初至今
        result = await sdk.call(
            "css",
            meta["code"],
            "NAME,NOW,CHGPCT,CHGPCTNYEAR",
        )
    except Exception as e:
        env, _ = err("CHOICE_CALL_FAILED", str(e))
        return JSONResponse(env)
    if meta["code"] not in result.Codes:
        env, _ = err("NO_DATA", f"行业指数 {meta['code']} 无数据", 200)
        return JSONResponse(env)
    row = result.Data[meta["code"]]
    val = dict(zip(result.Indicators, row))
    return JSONResponse(
        ok(
            {
                "name": meta["name"],
                "index_code": meta["code"],
                "index_value": val.get("NOW"),
                "change_pct": val.get("CHGPCT"),
                "ytd_return": val.get("CHGPCTNYEAR"),
            }
        )
    )


@app.get("/api/news")
async def get_news(
    query: str = Query("", description="关键词，空则返回最新"),
    limit: int = Query(15, ge=1, le=50),
) -> JSONResponse:
    fail = _require_sdk()
    if fail:
        return fail
    from datetime import datetime, timedelta

    end_d = datetime.utcnow().date()
    start_d = end_d - timedelta(days=2)
    try:
        # cfn 资讯函数：取最近 48h，按标题做 substring 过滤
        result = await sdk.call(
            "cfn",
            "",  # 全市场新闻；指定标的可填 600519.SH
            "TITLE,PUBLISHDATE,SOURCE",
            f"StartDate={start_d},EndDate={end_d},RowIndex=1",
        )
    except Exception as e:
        env, _ = err("CHOICE_CALL_FAILED", str(e))
        return JSONResponse(env)

    # cfn 返回结构：Data[code] = list of (title, date, source) for each item
    items: list[dict] = []
    q = (query or "").strip()
    for code in result.Codes or []:
        rows = result.Data.get(code) or []
        for row in rows:
            if not isinstance(row, (list, tuple)):
                continue
            title = str(row[0] or "")
            if not title:
                continue
            if q and q not in title:
                continue
            items.append(
                {
                    "title": title,
                    "datetime": str(row[1]) if len(row) > 1 else None,
                    "source": str(row[2]) if len(row) > 2 else None,
                }
            )
            if len(items) >= limit:
                break
        if len(items) >= limit:
            break

    return JSONResponse(ok({"query": q or None, "count": len(items), "items": items}))

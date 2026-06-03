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

from dotenv import load_dotenv  # 必须在 sdk 模块读 os.environ 之前调用
load_dotenv()

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
    """行情快照。
    实现细节：账号当前只开通历史数据，无实时行情权限（NOW / CHGPCT 报 service error），
    所以 price 取最近收盘价 + change_pct 自算 (last_close - prev_close) / prev_close。
    投研场景一日延迟可接受。"""
    fail = _require_sdk()
    if fail:
        return fail
    sym = normalize_symbol(symbol)
    from datetime import datetime, timedelta

    # 截面静态指标：名称 / 估值 / 当日量额（NOW 和 CHGPCT 没权限，绕开）
    try:
        css_r = await sdk.call("css", sym, "NAME,PETTM,PBMRQ")
    except Exception as e:
        env, _ = err("CHOICE_CALL_FAILED", f"css: {e}")
        return JSONResponse(env)
    if sym not in css_r.Codes:
        env, _ = err("NO_DATA", f"Choice 未返回 {sym} 的截面数据")
        return JSONResponse(env)
    static = dict(zip(css_r.Indicators, css_r.Data[sym]))

    # 近 7 个自然日的 CLOSE/VOLUME/AMOUNT —— 取倒数两根算最新价 + 日涨跌
    end_d = datetime.utcnow().date()
    start_d = end_d - timedelta(days=7)
    try:
        csd_r = await sdk.call(
            "csd",
            sym,
            "CLOSE,VOLUME,AMOUNT",
            start_d.strftime("%Y-%m-%d"),
            end_d.strftime("%Y-%m-%d"),
            "Period=1,AdjustFlag=1",
        )
    except Exception as e:
        env, _ = err("CHOICE_CALL_FAILED", f"csd: {e}")
        return JSONResponse(env)

    price = prev_price = change_pct = volume = amount = trade_date = None
    if sym in csd_r.Codes:
        closes = csd_r.Data[sym][0]  # CLOSE
        vols = csd_r.Data[sym][1]    # VOLUME
        amts = csd_r.Data[sym][2]    # AMOUNT
        dates = list(csd_r.Dates)
        # 末尾可能是 None（当天还没收盘）—— 从后往前找第一个非 None
        for i in range(len(closes) - 1, -1, -1):
            if closes[i] is not None:
                price = closes[i]
                volume = vols[i]
                amount = amts[i]
                trade_date = str(dates[i])
                # 再往前找一根算涨跌
                for j in range(i - 1, -1, -1):
                    if closes[j] is not None:
                        prev_price = closes[j]
                        break
                break
        if price is not None and prev_price:
            change_pct = round((price - prev_price) / prev_price * 100, 2)

    payload = {
        "symbol": sym,
        "name": static.get("NAME"),
        "price": price,
        "change_pct": change_pct,
        "pe": static.get("PETTM"),
        "pb": static.get("PBMRQ"),
        "volume": volume,
        "amount": amount,
        "trade_date": trade_date,
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
    """行业指数概览。
    实现与 get_price 同思路：实时 NOW/CHGPCT 和 CHGPCTNYEAR(YTD) 账号无权限，
    用 CLOSE 历史序列自算最新值 + 日涨跌 + YTD（从年初首根 vs 最近一根）。"""
    fail = _require_sdk()
    if fail:
        return fail
    meta = lookup_industry(industry)
    if not meta:
        env, _ = err("UNKNOWN_INDUSTRY", f"没有指数映射：{industry}", 200)
        return JSONResponse(env)
    code = meta["code"]
    from datetime import datetime, timedelta

    # 名称（静态指标）
    try:
        css_r = await sdk.call("css", code, "NAME")
    except Exception as e:
        env, _ = err("CHOICE_CALL_FAILED", f"css: {e}")
        return JSONResponse(env)

    # CLOSE 序列：从去年年底拉到今天，覆盖 YTD 区间
    today = datetime.utcnow().date()
    start_d = today.replace(month=1, day=1) - timedelta(days=10)  # 留余量取年初首根
    try:
        csd_r = await sdk.call(
            "csd",
            code,
            "CLOSE",
            start_d.strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d"),
            "Period=1,AdjustFlag=1",
        )
    except Exception as e:
        env, _ = err("CHOICE_CALL_FAILED", f"csd: {e}")
        return JSONResponse(env)

    index_value = change_pct = ytd_return = trade_date = ytd_start_value = None
    if code in csd_r.Codes:
        closes = csd_r.Data[code][0]
        dates = list(csd_r.Dates)
        # 倒序找最新一根非 None
        last_i = None
        for i in range(len(closes) - 1, -1, -1):
            if closes[i] is not None:
                last_i = i
                index_value = closes[i]
                trade_date = str(dates[i])
                break
        # 日涨跌：再往前找一根
        if last_i is not None:
            for j in range(last_i - 1, -1, -1):
                if closes[j] is not None:
                    change_pct = round((closes[last_i] - closes[j]) / closes[j] * 100, 2)
                    break
        # YTD：找今年 1/1 之后的第一根（约等于年初首个交易日的收盘）
        year_start = today.replace(month=1, day=1).strftime("%Y/%m/%d")
        for k, d in enumerate(dates):
            if str(d) >= year_start and closes[k] is not None:
                ytd_start_value = closes[k]
                break
        if ytd_start_value and index_value:
            ytd_return = round((index_value - ytd_start_value) / ytd_start_value * 100, 2)

    name = csd_r.Codes and meta["name"]
    if css_r.ErrorCode == 0 and code in css_r.Codes:
        # 用 SDK 返回的官方名优先
        name = css_r.Data[code][0] or meta["name"]

    return JSONResponse(
        ok(
            {
                "name": name,
                "index_code": code,
                "index_value": index_value,
                "change_pct": change_pct,
                "ytd_return": ytd_return,
                "trade_date": trade_date,
            }
        )
    )


@app.get("/api/news")
async def get_news(
    symbol: str = Query("", description="标的代码（必填，cfn 不支持全市场）"),
    query: str = Query("", description="关键词过滤（在标题里 substring 匹配）"),
    limit: int = Query(15, ge=1, le=50),
) -> JSONResponse:
    """资讯查询。
    SDK 签名：cfn(codes, content, mode, options)
      - codes: 单只标的（不支持全市场空串）
      - content: "companynews" / "industrynews" / "sectornews" / "report"
      - mode: 1 = StartToEnd 区间模式（需 starttime+endtime）
      - options: starttime/endtime 14 位时间戳

    注：账号 njnbt0001 当前**无 cfn 权限**（returnMsg:'无权限[10001]'），
    本接口会返回 INSUFFICIENT_ACCESS，让 DataSource 落到下一层 provider。"""
    fail = _require_sdk()
    if fail:
        return fail
    if not symbol:
        env, _ = err("MISSING_SYMBOL", "Choice cfn 必须指定 symbol，不支持全市场新闻")
        return JSONResponse(env)
    sym = normalize_symbol(symbol)
    from datetime import datetime, timedelta

    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=7)
    options = (
        f"starttime={start_dt.strftime('%Y%m%d%H%M%S')},"
        f"endtime={end_dt.strftime('%Y%m%d%H%M%S')}"
    )
    try:
        result = await sdk.call("cfn", sym, "companynews", 1, options)
    except Exception as e:
        msg = str(e)
        # SDK 在权限不足时会以 RuntimeError 抛 ErrorCode=10001012
        if "10001012" in msg:
            env, _ = err("INSUFFICIENT_ACCESS", "Choice 账号未开通资讯查询权限")
            return JSONResponse(env)
        env, _ = err("CHOICE_CALL_FAILED", msg)
        return JSONResponse(env)

    items: list[dict] = []
    q = (query or "").strip()
    for code in result.Codes or []:
        rows = result.Data.get(code) or []
        for row in rows:
            if not isinstance(row, (list, tuple)):
                continue
            title = str(row[0] or "")
            if not title or (q and q not in title):
                continue
            items.append({
                "title": title,
                "datetime": str(row[1]) if len(row) > 1 else None,
                "source": str(row[2]) if len(row) > 2 else None,
            })
            if len(items) >= limit:
                break
        if len(items) >= limit:
            break

    return JSONResponse(ok({"symbol": sym, "query": q or None, "count": len(items), "items": items}))

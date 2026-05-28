"""Mock 数据 provider。永远作为链上最后一环兜底，保证没接外部数据源
时演示也能跑通。

标的覆盖 A 股 + 美股科技股；数值仅供演示，不是真实行情。
宏观 / 行业数据同样是占位数据，等 M3.1 接上 Tushare 真端点后逐步替换。
"""

from __future__ import annotations

import hashlib
import random
import re
from datetime import date, timedelta

from app.data.providers.base import DataProvider


def _normalize_symbol(symbol: str) -> str:
    """把裸 6 位 A 股代码归一化成带后缀的标准形式：`600519` → `600519.SH`。"""
    s = symbol.upper().strip()
    if "." in s or not re.fullmatch(r"\d{6}", s):
        return s
    first = s[0]
    if first == "6":
        return f"{s}.SH"
    if first in ("0", "3"):
        return f"{s}.SZ"
    if first in ("8", "4"):
        return f"{s}.BJ"
    return s

# ---------- 行情快照（演示数据） ----------

_PRICES: dict[str, dict] = {
    # A 股
    "600519.SH": {"name": "贵州茅台", "price": 1820.50, "change_pct": -1.23, "pe": 28.4, "industry": "白酒"},
    "000858.SZ": {"name": "五粮液",   "price": 142.30,  "change_pct": -0.42, "pe": 17.8, "industry": "白酒"},
    "300750.SZ": {"name": "宁德时代", "price": 245.30,  "change_pct": -2.10, "pe": 18.7, "industry": "锂电池"},
    "002594.SZ": {"name": "比亚迪",   "price": 256.80,  "change_pct": 1.05,  "pe": 22.4, "industry": "新能源汽车"},
    "000001.SZ": {"name": "平安银行", "price": 11.85,   "change_pct": 0.51,  "pe": 5.2,  "industry": "银行"},
    "600036.SH": {"name": "招商银行", "price": 36.42,   "change_pct": 0.83,  "pe": 6.9,  "industry": "银行"},
    "601318.SH": {"name": "中国平安", "price": 48.20,   "change_pct": -0.30, "pe": 7.6,  "industry": "保险"},
    "600276.SH": {"name": "恒瑞医药", "price": 47.85,   "change_pct": 0.62,  "pe": 51.3, "industry": "创新药"},
    "300059.SZ": {"name": "东方财富", "price": 14.62,   "change_pct": 1.74,  "pe": 23.1, "industry": "证券"},
    "688981.SH": {"name": "中芯国际", "price": 71.40,   "change_pct": 2.15,  "pe": 78.9, "industry": "半导体"},
    "002415.SZ": {"name": "海康威视", "price": 32.45,   "change_pct": -0.55, "pe": 19.2, "industry": "安防"},
    "600900.SH": {"name": "长江电力", "price": 27.86,   "change_pct": 0.18,  "pe": 21.3, "industry": "公用事业"},
    # 美股科技
    "AAPL":      {"name": "Apple",    "price": 187.42, "change_pct": 0.83,  "pe": 31.2, "industry": "消费电子"},
    "MSFT":      {"name": "Microsoft","price": 412.30, "change_pct": 1.10,  "pe": 35.4, "industry": "软件"},
    "NVDA":      {"name": "NVIDIA",   "price": 880.50, "change_pct": 2.35,  "pe": 65.8, "industry": "半导体"},
    "TSLA":      {"name": "Tesla",    "price": 178.90, "change_pct": -1.85, "pe": 45.6, "industry": "电动汽车"},
}

# ---------- 宏观指标（演示用最新读数） ----------

_MACRO: dict[str, dict] = {
    "cpi": {
        "name": "CPI 同比",
        "value": 0.4,
        "unit": "%",
        "period": "2026-04",
        "trend": "继续低位运行；非食品项疲软；服务通胀温和",
    },
    "ppi": {
        "name": "PPI 同比",
        "value": -1.8,
        "unit": "%",
        "period": "2026-04",
        "trend": "通缩压力延续；上游金属与化工拖累",
    },
    "m2": {
        "name": "M2 同比",
        "value": 7.1,
        "unit": "%",
        "period": "2026-04",
        "trend": "增速边际放缓；信用扩张动能不足",
    },
    "pmi_manufacturing": {
        "name": "制造业 PMI",
        "value": 50.2,
        "unit": "指数",
        "period": "2026-04",
        "trend": "勉强站上荣枯线；新订单分项偏弱",
    },
    "pmi_non_manufacturing": {
        "name": "非制造业 PMI",
        "value": 51.8,
        "unit": "指数",
        "period": "2026-04",
        "trend": "服务业景气尚可；建筑业回升",
    },
    "interest_rate_10y": {
        "name": "10 年期国债收益率",
        "value": 2.38,
        "unit": "%",
        "period": "2026-05-27",
        "trend": "持续低位震荡；机构配置盘主导",
    },
    "us_fed_funds_rate": {
        "name": "美联储基金利率上限",
        "value": 4.50,
        "unit": "%",
        "period": "2026-05",
        "trend": "本年内已降息两次；市场预期年内还有 1-2 次",
    },
    "usd_cny": {
        "name": "美元兑人民币",
        "value": 7.18,
        "unit": "",
        "period": "2026-05-27",
        "trend": "在 7.15-7.25 区间窄幅波动；央行维持中间价稳定",
    },
    "social_financing": {
        "name": "社融存量同比",
        "value": 8.3,
        "unit": "%",
        "period": "2026-04",
        "trend": "增速稳定但居民信贷需求疲软；政府债是主要贡献",
    },
}

# ---------- 行业概览（演示数据） ----------

_INDUSTRIES: dict[str, dict] = {
    "白酒": {
        "name": "白酒",
        "avg_pe": 24.6,
        "ytd_return": -3.2,
        "top_constituents": ["贵州茅台", "五粮液", "泸州老窖", "山西汾酒"],
        "trend": "高端消费场景偏弱；批价承压；行业进入主动去库存阶段",
        "key_drivers": ["商务消费修复节奏", "批价企稳信号", "消费税改革预期"],
    },
    "锂电池": {
        "name": "锂电池",
        "avg_pe": 21.4,
        "ytd_return": 5.8,
        "top_constituents": ["宁德时代", "比亚迪", "亿纬锂能", "国轩高科"],
        "trend": "产能过剩压制价格；龙头通过技术与海外份额维持壁垒；储能需求成为新增量",
        "key_drivers": ["碳酸锂价格", "全球电动车渗透率", "储能装机增速", "海外贸易壁垒"],
    },
    "新能源汽车": {
        "name": "新能源汽车",
        "avg_pe": 28.7,
        "ytd_return": 4.1,
        "top_constituents": ["比亚迪", "理想汽车", "蔚来", "小鹏汽车"],
        "trend": "国内渗透率超过 50%；价格战仍在；高端化与智能化是分化主线",
        "key_drivers": ["智驾技术拐点", "出海销量", "电池成本", "国家以旧换新政策"],
    },
    "银行": {
        "name": "银行",
        "avg_pe": 5.8,
        "ytd_return": 9.4,
        "top_constituents": ["工商银行", "建设银行", "招商银行", "兴业银行"],
        "trend": "净息差继续收窄但已有企稳迹象；高股息属性持续吸引避险资金",
        "key_drivers": ["LPR 调整", "地产链不良率", "化债节奏", "存款利率市场化"],
    },
    "半导体": {
        "name": "半导体",
        "avg_pe": 62.4,
        "ytd_return": 12.8,
        "top_constituents": ["中芯国际", "韦尔股份", "北方华创", "海光信息"],
        "trend": "国产替代主线持续；AI 算力需求拉动设备与封测；地缘风险敏感",
        "key_drivers": ["国产化率", "全球资本开支", "AI 推理芯片放量", "出口管制变化"],
    },
    "创新药": {
        "name": "创新药",
        "avg_pe": 48.6,
        "ytd_return": -2.8,
        "top_constituents": ["恒瑞医药", "百济神州", "信达生物", "君实生物"],
        "trend": "出海 license-out 持续；医保谈判温和；国内创新药支付端待破局",
        "key_drivers": ["FDA 审批结果", "BD 交易首付款", "医保乙类目录", "美元利率变化"],
    },
    "证券": {
        "name": "证券",
        "avg_pe": 22.8,
        "ytd_return": 7.6,
        "top_constituents": ["中信证券", "华泰证券", "东方财富", "中金公司"],
        "trend": "成交量回暖；财富管理与机构业务持续分化；牌照价值受合并预期支撑",
        "key_drivers": ["日均成交额", "IPO 节奏", "并购预期", "公募费率改革后续"],
    },
    "公用事业": {
        "name": "公用事业",
        "avg_pe": 19.2,
        "ytd_return": 11.5,
        "top_constituents": ["长江电力", "国投电力", "华能水电", "中国核电"],
        "trend": "高股息防御属性突出；电改持续推进电价市场化",
        "key_drivers": ["来水情况", "电价改革", "煤价", "新能源装机"],
    },
}


# ---------- 行业名别名（用户输入容错） ----------

# ---------- 新闻（演示样本） ----------

_NEWS_FIXTURES: list[dict] = [
    {
        "datetime": "2026-05-28 09:15:00",
        "title": "央行公开市场净投放 4200 亿元，市场流动性整体宽松",
        "content": "央行今日开展 6000 亿元 7 天逆回购，到期 1800 亿元，净投放 4200 亿元。机构解读认为月末流动性平稳。",
        "channel": "宏观",
    },
    {
        "datetime": "2026-05-28 08:30:00",
        "title": "白酒板块批价持续承压，茅台飞天批价跌破 2300",
        "content": "上海/北京等地经销商反映，飞天茅台 53 度散瓶批价已跌破 2300 元，较年初下行约 8%。",
        "channel": "白酒",
    },
    {
        "datetime": "2026-05-28 07:45:00",
        "title": "宁德时代发布新一代 6C 超充电池，量产时间表前置至四季度",
        "content": "公司称新电池能量密度提升 15%，目标年内进入装车阶段。",
        "channel": "锂电池",
    },
    {
        "datetime": "2026-05-27 19:30:00",
        "title": "美联储 6 月议息会议预期：市场押注降息概率上升至 60%",
        "content": "CME FedWatch 数据显示，市场对 6 月降息 25bp 的概率从上周的 45% 上升至 60%。",
        "channel": "宏观",
    },
    {
        "datetime": "2026-05-27 18:10:00",
        "title": "半导体设备国产化率突破 35%，AI 算力需求拉动设备投资",
        "content": "国内主流晶圆厂 2026 年资本开支同比增长 22%，关键设备国产替代加速。",
        "channel": "半导体",
    },
    {
        "datetime": "2026-05-27 16:00:00",
        "title": "比亚迪 4 月新能源车销量同比+18%，出口创新高",
        "content": "公司 4 月销售新能源车 39.6 万辆，其中出口 6.8 万辆，同比增长 65%。",
        "channel": "新能源汽车",
    },
    {
        "datetime": "2026-05-27 14:20:00",
        "title": "招商银行一季报：净息差企稳，财富管理收入同比+12%",
        "content": "公司一季度净息差环比+2bp 至 1.98%，非息收入占比提升至 42%。",
        "channel": "银行",
    },
    {
        "datetime": "2026-05-27 11:00:00",
        "title": "国家医保局：今年医保谈判温和，重点支持创新药",
        "content": "针对创新药品类，今年医保谈判平均降幅控制在 35% 以内，较去年放缓。",
        "channel": "创新药",
    },
    {
        "datetime": "2026-05-26 21:30:00",
        "title": "苹果 WWDC 2026 预热：传将发布更大规模 AI 模型与端侧推理框架",
        "content": "彭博社引述供应链消息称，苹果将公布与 OpenAI 合作的全新 AI 战略。",
        "channel": "消费电子",
    },
    {
        "datetime": "2026-05-26 20:00:00",
        "title": "NVIDIA Q1 财报超预期：数据中心营收同比+62%",
        "content": "公司数据中心营收 280 亿美元，毛利率 75.1%，指引 Q2 营收 320 亿美元。",
        "channel": "半导体",
    },
]


_INDUSTRY_ALIASES: dict[str, str] = {
    "酒": "白酒",
    "白酒板块": "白酒",
    "高端白酒": "白酒",
    "动力电池": "锂电池",
    "电池": "锂电池",
    "新能源车": "新能源汽车",
    "电动车": "新能源汽车",
    "新能源": "新能源汽车",
    "金融": "银行",
    "银行业": "银行",
    "芯片": "半导体",
    "半导体行业": "半导体",
    "医药": "创新药",
    "创新药板块": "创新药",
    "券商": "证券",
    "电力": "公用事业",
    "电力行业": "公用事业",
}


class MockProvider(DataProvider):
    name = "mock"

    async def get_price(self, symbol: str) -> dict | None:
        sym = _normalize_symbol(symbol)
        row = _PRICES.get(sym)
        if not row:
            return None
        return {"symbol": sym, **row}

    async def get_macro_indicator(self, indicator: str) -> dict | None:
        key = indicator.lower().strip()
        row = _MACRO.get(key)
        if not row:
            return None
        return {"indicator": key, **row}

    async def get_industry_overview(self, industry: str) -> dict | None:
        key = industry.strip()
        canonical = _INDUSTRY_ALIASES.get(key, key)
        row = _INDUSTRIES.get(canonical)
        if not row:
            return None
        return dict(row)

    async def search_news(
        self,
        query: str | None = None,
        limit: int = 20,
    ) -> dict | None:
        q = (query or "").strip()
        items: list[dict] = []
        for n in _NEWS_FIXTURES:
            if q and q not in n["title"] and q not in (n.get("content") or "") and q != n.get("channel"):
                continue
            items.append(dict(n))
            if len(items) >= max(1, min(limit, 50)):
                break
        return {"query": q or None, "count": len(items), "items": items}

    async def get_kline(self, symbol: str, days: int = 30) -> dict | None:
        sym = _normalize_symbol(symbol)
        row = _PRICES.get(sym)
        if not row:
            return None
        days = max(5, min(days, 120))  # 限制在 5-120 之间
        bars = _generate_kline_bars(sym, anchor_close=row["price"], days=days)
        latest = bars[-1]
        first = bars[0]
        change_pct = (latest["close"] - first["close"]) / first["close"] * 100.0
        return {
            "symbol": sym,
            "name": row["name"],
            "days": days,
            "anchor_close": row["price"],
            "summary": {
                "range_high": max(b["high"] for b in bars),
                "range_low": min(b["low"] for b in bars),
                "range_pct_chg": round(change_pct, 2),
                "avg_volume": int(sum(b["volume"] for b in bars) / len(bars)),
            },
            "bars": bars,
        }


def _generate_kline_bars(
    symbol: str, *, anchor_close: float, days: int
) -> list[dict]:
    """以 symbol 为种子的确定性 OHLCV 随机游走 —— 同一标的反复调用结果一致。

    把**最新一根**的 close 锚定到 `anchor_close`（与行情快照 mock 保持同步），
    然后用 symbol 种子的随机数源向前倒推每日对数收益率。
    """
    seed = int(hashlib.md5(symbol.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)

    # 日对数收益率标准差：A 股约 1.8% / 美股大盘股约 1.5%；mock 用中间值够用
    daily_sigma = 0.018

    closes: list[float] = [anchor_close]
    for _ in range(days - 1):
        # 向前倒推：前一日收盘 = 今日收盘 / (1+ret)
        ret = rng.gauss(0, daily_sigma)
        prev = closes[-1] / (1.0 + ret)
        closes.append(prev)
    closes.reverse()  # 最旧的放最前

    today = date.today()
    # 粗暴跳过周末
    dates: list[date] = []
    cur = today
    while len(dates) < days:
        if cur.weekday() < 5:
            dates.append(cur)
        cur -= timedelta(days=1)
    dates.reverse()

    bars: list[dict] = []
    prev_close: float | None = None
    for d, c in zip(dates, closes):
        open_ = c * (1 + rng.gauss(0, daily_sigma / 2))
        high = max(open_, c) * (1 + abs(rng.gauss(0, daily_sigma / 2)))
        low = min(open_, c) * (1 - abs(rng.gauss(0, daily_sigma / 2)))
        volume = int(rng.uniform(0.7, 1.4) * 1_500_000)
        pct_chg = ((c - prev_close) / prev_close * 100.0) if prev_close else 0.0
        bars.append(
            {
                "date": d.isoformat(),
                "open": round(open_, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(c, 2),
                "volume": volume,
                "pct_chg": round(pct_chg, 2),
            }
        )
        prev_close = c
    return bars


def known_macro_indicators() -> list[str]:
    return list(_MACRO.keys())


def known_industries() -> list[str]:
    return list(_INDUSTRIES.keys())

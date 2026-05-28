"""我们的抽象指标名 ↔ Choice 原生 ID / 代码 的映射表。

数据源更换时，只要在这里改映射，对外暴露的语义保持稳定。
"""

from __future__ import annotations

# ---------- 宏观指标：我们的 key → Choice EDB ID ----------
# Choice EDB ID 参考：终端"宏观数据 → 命令生成"
# 这里给的是有代表性的常用 ID，覆盖率随后再细化
MACRO_EDB_IDS: dict[str, dict[str, str]] = {
    "cpi": {
        "id": "EMM00087117",  # 居民消费价格指数:当月同比
        "name": "CPI 同比",
        "unit": "%",
    },
    "ppi": {
        "id": "EMM00087236",  # 工业生产者出厂价格指数:当月同比
        "name": "PPI 同比",
        "unit": "%",
    },
    "m2": {
        "id": "EMM00121980",  # M2 同比
        "name": "M2 同比",
        "unit": "%",
    },
    "pmi_manufacturing": {
        "id": "EMM00122222",  # 制造业 PMI
        "name": "制造业 PMI",
        "unit": "指数",
    },
    "pmi_non_manufacturing": {
        "id": "EMM00122223",  # 非制造业 PMI（占位 ID）
        "name": "非制造业 PMI",
        "unit": "指数",
    },
    "interest_rate_10y": {
        "id": "EMM00166466",  # 10 年期国债到期收益率
        "name": "10 年期国债收益率",
        "unit": "%",
    },
    "social_financing": {
        "id": "EMM00121935",  # 社会融资规模存量同比
        "name": "社会融资规模存量同比",
        "unit": "%",
    },
    "usd_cny": {
        "id": "EMM00166469",  # 美元兑人民币中间价
        "name": "美元兑人民币中间价",
        "unit": "",
    },
}


def lookup_macro(key: str) -> dict | None:
    return MACRO_EDB_IDS.get(key.lower().strip())


# ---------- 行业 → 申万一级行业指数代码 ----------
INDUSTRY_INDEX_CODES: dict[str, dict[str, str]] = {
    "白酒":         {"code": "801124.SI", "name": "白酒（申万）"},
    "锂电池":       {"code": "801737.SI", "name": "锂电池（申万）"},
    "新能源汽车":   {"code": "801737.SI", "name": "新能源汽车（申万二级，待校正）"},
    "银行":         {"code": "801780.SI", "name": "银行（申万）"},
    "半导体":       {"code": "801081.SI", "name": "半导体（申万二级）"},
    "创新药":       {"code": "801151.SI", "name": "化学制药（申万二级，最接近）"},
    "证券":         {"code": "801193.SI", "name": "证券（申万）"},
    "公用事业":     {"code": "801160.SI", "name": "公用事业（申万）"},
}

# 别名归一化（与 backend MockProvider 保持一致）
INDUSTRY_ALIASES: dict[str, str] = {
    "动力电池": "锂电池",
    "电池": "锂电池",
    "新能源车": "新能源汽车",
    "电动车": "新能源汽车",
    "新能源": "新能源汽车",
    "芯片": "半导体",
    "金融": "银行",
    "券商": "证券",
    "电力": "公用事业",
    "酒": "白酒",
}


def lookup_industry(name: str) -> dict | None:
    n = name.strip()
    canonical = INDUSTRY_ALIASES.get(n, n)
    row = INDUSTRY_INDEX_CODES.get(canonical)
    if not row:
        return None
    return {"key": canonical, **row}


# ---------- A 股代码归一化（与 backend Mock / Tushare 保持一致）----------

import re


def normalize_symbol(symbol: str) -> str:
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

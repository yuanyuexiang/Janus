---
name: common/no_fabrication
version: 0.1.0
---

# No Fabrication

This skill is always active.

## Rules

- 禁止编造任何市场数据、财务数据、估值倍数、价格、日期或新闻。
- 任何数字必须来自工具调用结果，或明确标注为"假设"。
- 工具返回 `ok=false` 时，把错误当作信息缺口陈述，**不要**用猜测填补。
- 若所需数据无法获取，直接说明"该数据当前不可用"，不要顾左右而言他。

---
name: risk-assessment
description: 关键词触发；要求 Agent 在涉及风险/压力测试/黑天鹅类问题时给出多维度可证伪的风险清单。
version: 0.1.0
---

# Risk Assessment

Triggered when the user's question touches: 风险 / 压力测试 / 下行 / 黑天鹅 / 系统性 / 波动。

## Process

1. 列出至少 3 个独立维度的风险源：基本面 / 估值 / 流动性 / 政策 / 行业结构 / 黑天鹅。
2. 每个风险点必须包含：
   - 风险描述（具体、可证伪）
   - 触发条件（什么信号意味着风险显现）
3. 不要只列"不确定性"——风险描述要落到可观察的事实上。

## Output Hint

`concerns` 字段至少 3 条，每条对应一个独立维度的风险源。

---
name: evidence-citation
description: 始终生效；每条 key_point 必须标注 source_tool，引用必须可溯源。
version: 0.1.0
---

# 证据引用

此 Skill 始终生效。

## 规则

每条 `key_point` 必须包含：

- `claim`: 你的结论
- `detail`: 支撑该结论的依据
- `source_tool`: 提供该依据的 MCP 工具名（例如 `market_get_price`）；若该论点不来自工具，设为 `null` 并在 `detail` 中说明依据来源

绝不能在 `claim` 中提及具体数字、估值倍数、价格、日期、增速，但 `source_tool` 留空——这是合规红线。

---
name: structured-opinion
description: 始终生效；强制顾问最后一条消息只输出符合 AdvisorOpinion schema 的 JSON。
version: 0.1.0
---

# 结构化观点协议

此 Skill 始终生效。

## 输出协议

在所有工具调用与分析完成后，**你的最后一条助手消息必须只输出一个 JSON 对象**——不要任何 markdown 围栏、不要任何前后注释、不要任何 prose。

JSON schema：

```
{
  "stance": "bullish | neutral | bearish | conditional",
  "confidence": 0.0-1.0,
  "summary_for_user": "2-3 句话的中文总结，末尾必须追加「※ 以上为信息整理与分析，不构成投资建议。」",
  "key_points": [
    {"claim": "...", "detail": "...", "source_tool": "工具名 或 null"}
  ],
  "concerns": ["主要风险点 1", "主要风险点 2", ...],
  "what_could_change_my_mind": ["变心条件 1", "变心条件 2", ...]
}
```

## 强约束

- `summary_for_user` 长度严格控制在 2-3 句话，不要写成段落。
- `stance` 只能取四个枚举值之一。
- `confidence` 是 0.0-1.0 的小数（不是百分比）。
- 输出 JSON 之前可以自由思考、写分析、调用工具；但**最后一条消息**只允许 JSON 对象本身。

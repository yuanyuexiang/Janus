"""Conductor's synthesis: given N advisor opinions, produce a CouncilSummary.

Streams the conductor's user-facing prose; emits the structured summary at the end.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

from app.config import get_settings
from app.llm.client import get_client
from app.orchestrator.protocol import AdvisorOpinion, CouncilSummary
from app.orchestrator.runner import _extract_json_object

logger = logging.getLogger(__name__)


CONDUCTOR_SYSTEM_PROMPT = """\
你是「执棋」，圆桌投研的主持人。

## 你的职责

你**不**输出独立的投资观点。你的工作是把几位顾问的发言结构化整合：

1. 提取**共识**（多数顾问观察一致的事实/判断）
2. 标注**分歧**（不同立场的核心论据各是什么）
3. 提炼**关键变量**（影响整桌判断的最核心 3-5 个因素，来源于顾问们的 `what_could_change_my_mind`）
4. 构建**风险地图**（合并顾问们的 `concerns`，按严重度 1-5 评分，给出缓释思路）
5. 写一段**给用户的总结**（不超过 100 字，强调"决策权在用户"）

## 输出协议

**最后一条助手消息必须只输出一个 JSON 对象**，schema：

```
{
  "verdict": "strong_consensus | weak_consensus | split",
  "consensus": ["共识点 1", "共识点 2", ...],
  "disagreements": [
    {"point": "分歧点", "sides": {"bullish": ["..."], "bearish": ["..."]}}
  ],
  "key_variables": ["变量 1", "变量 2", ...],
  "risk_map": [
    {"risk": "...", "severity": 1-5, "mitigation": "..."}
  ],
  "final_summary": "100 字左右总结，末尾必须追加「※ 决策权在您手上。」"
}
```

## 共识度判定

- 若 ≥70% 顾问立场相同 → `strong_consensus`
- 若 ≥50% 立场相同 → `weak_consensus`
- 否则 → `split`

## 合规铁律

- 永远不说"建议买入/卖出/持有"
- 不预测短期走势
- `final_summary` 必须以「※ 决策权在您手上。」结尾
"""


def _build_synthesis_prompt(question: str, opinions: list[AdvisorOpinion]) -> str:
    parts = [
        f"用户原始提问：\n{question}\n",
        "以下是各位顾问的结构化观点：\n",
    ]
    for op in opinions:
        parts.append(
            f"### {op.agent} (stance={op.stance}, confidence={op.confidence})\n"
            f"```json\n{json.dumps(op.model_dump(), ensure_ascii=False, indent=2)}\n```\n"
        )
    parts.append(
        "\n请按照系统提示中的协议综合输出。"
        "可以先用自然语言展开分析（给用户阅读），"
        "**最后一条消息**只输出 CouncilSummary JSON 对象。"
    )
    return "\n".join(parts)


async def synthesize(
    *,
    question: str,
    opinions: list[AdvisorOpinion],
    client: AsyncAnthropic | None = None,
    model: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield synthesis events:
      {"type": "synthesis_text", "chunk": "..."}        # streamed prose
      {"type": "synthesis", "full": CouncilSummary}     # final structured
      {"type": "error", "code": "...", "message": "..."}
    """
    settings = get_settings()
    client = client or get_client()
    model = model or settings.conductor_model

    if not opinions:
        yield {
            "type": "error",
            "code": "NO_OPINIONS",
            "message": "No advisor opinions to synthesize",
        }
        return

    prompt = _build_synthesis_prompt(question, opinions)
    accumulated = ""

    async with client.messages.stream(
        model=model,
        max_tokens=6144,
        system=CONDUCTOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for event in stream:
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                chunk = event.delta.text
                accumulated += chunk
                yield {"type": "synthesis_text", "chunk": chunk}
        final_msg = await stream.get_final_message()

    logger.warning(
        "Synthesizer first-pass: text_len=%d, stop_reason=%s",
        len(accumulated),
        final_msg.stop_reason,
    )

    parsed = _extract_json_object(
        accumulated, required_keys=["verdict", "final_summary"]
    )
    if parsed is None:
        logger.warning(
            "Synthesis JSON parse failed (first try, text_len=%d, stop=%s); retrying JSON-only.",
            len(accumulated),
            final_msg.stop_reason,
        )
        # Clean retry: fresh prompt that explicitly asks for JSON only,
        # without contaminating the conversation with the truncated first attempt.
        retry_messages = [
            {
                "role": "user",
                "content": (
                    prompt
                    + "\n\n---\n\n"
                    + "现在请**只输出**一个 CouncilSummary JSON 对象。"
                    "不要任何 prose、不要 markdown 围栏、不要 ```json 代码块。"
                    "直接以 `{` 开头，`}` 结尾。"
                ),
            }
        ]
        retry_text = ""
        async with client.messages.stream(
            model=model,
            max_tokens=6144,
            system=CONDUCTOR_SYSTEM_PROMPT,
            messages=retry_messages,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    retry_text += event.delta.text
            retry_final = await stream.get_final_message()
        logger.warning(
            "Synthesizer retry: text_len=%d, stop_reason=%s",
            len(retry_text),
            retry_final.stop_reason,
        )
        parsed = _extract_json_object(
            retry_text, required_keys=["verdict", "final_summary"]
        )

    if parsed is None:
        yield {
            "type": "error",
            "code": "SYNTHESIS_PARSE_FAILED",
            "message": "Conductor did not produce a valid CouncilSummary JSON after retry",
        }
        return

    try:
        summary = CouncilSummary.model_validate(parsed)
    except Exception as e:
        yield {
            "type": "error",
            "code": "SYNTHESIS_VALIDATION_FAILED",
            "message": f"{type(e).__name__}: {e}",
        }
        return

    yield {"type": "synthesis", "full": summary.model_dump()}

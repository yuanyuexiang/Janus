"""单顾问运行器：驱动一次 LLM tool-use 循环（OpenAI / litellm 格式），把过程包装成事件流。"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from app.llm.client import stream_chat
from app.mcp_client.manager import get_manager
from app.orchestrator.advisors.base import BaseAdvisor
from app.orchestrator.protocol import AdvisorOpinion
from app.orchestrator.skills.registry import get_skill_registry

logger = logging.getLogger(__name__)

MAX_TOOL_TURNS = 6


def _extract_json_object(
    text: str, required_keys: list[str] | None = None
) -> dict[str, Any] | None:
    """从 `text` 中提取一个 JSON 对象，容忍前后的散文 / markdown 围栏。

    策略：
      1. 剥掉 ``` 或 ```json 围栏。
      2. 正向扫描，记录所有 depth==0 的平衡 `{...}` 跨度。
      3. 如果指定了 `required_keys`，优先返回**最后一个**包含全部 required keys
         的跨度（避开 disagreements 里的嵌套 `{"bullish": [...]}` 这种内层对象）。
      4. 否则退化为最后一个能解析的对象。
    """
    if not text:
        return None
    stripped = re.sub(r"```(?:json)?", "", text)

    spans: list[tuple[int, int]] = []
    depth = 0
    start: int | None = None
    for i, c in enumerate(stripped):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            if depth == 0:
                continue  # 孤立的 }，忽略
            depth -= 1
            if depth == 0 and start is not None:
                spans.append((start, i))
                start = None

    if not spans:
        return None

    # 第一轮：从后往前找包含全部 required keys 的跨度
    if required_keys:
        for s, e in reversed(spans):
            try:
                obj = json.loads(stripped[s : e + 1])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and all(k in obj for k in required_keys):
                return obj

    # 兜底：从后往前找任意可解析的对象
    for s, e in reversed(spans):
        try:
            obj = json.loads(stripped[s : e + 1])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj

    return None


async def run_advisor(
    advisor: BaseAdvisor,
    question: str,
    *,
    model: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """驱动一位顾问完整一轮推理，把过程包装成事件流。

    事件类型：
      {type: "advisor_start", advisor, display, role, color}
      {type: "text", chunk}                       # 流式文本增量
      {type: "tool_call", tool, args}             # 模型请求调用工具
      {type: "tool_result", tool, result}         # 我们 handler 的返回
      {type: "opinion", full}                     # 最终结构化 AdvisorOpinion（dict）
      {type: "stage", stage: "thinking"|"tool_use"|"done"}
      {type: "error", code, message}
    """
    # model=None → stream_chat 用 advisor 角色的默认模型；advisor.model 是按顾问的覆盖
    model = model or advisor.model

    mcp = get_manager()
    tool_specs = mcp.openai_specs(advisor.allowed_tools)

    skill_registry = get_skill_registry()
    active_skills = skill_registry.resolve(question=question, agent=advisor.profile.name)
    skill_texts = skill_registry.load_texts(active_skills)
    composed_system_prompt = "\n\n".join(
        [advisor.system_prompt(), "# Active Skills", "\n\n---\n\n".join(skill_texts)]
    )

    yield {
        "type": "advisor_start",
        "advisor": advisor.profile.name,
        "display": advisor.profile.display,
        "role": advisor.profile.role,
        "color": advisor.profile.color,
        "active_skills": active_skills,
    }

    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    accumulated_text = ""
    tokens_in = 0
    tokens_out = 0

    for _turn in range(MAX_TOOL_TURNS):
        yield {"type": "stage", "stage": "thinking"}

        done: dict[str, Any] | None = None
        async for ev in stream_chat(
            role="advisor",
            model_override=model,
            messages=messages,
            system=composed_system_prompt,
            tools=tool_specs or None,
            max_tokens=2048,
        ):
            if ev["type"] == "text":
                accumulated_text += ev["chunk"]
                yield {"type": "text", "chunk": ev["chunk"]}
            elif ev["type"] == "done":
                done = ev

        if done:
            tokens_in += done["tokens_in"]
            tokens_out += done["tokens_out"]

        tool_calls = done["tool_calls"] if done else []
        if not tool_calls:
            break

        # OpenAI 格式：先追加带 tool_calls 的 assistant 消息，再逐个追加 role=tool 的结果
        messages.append(
            {
                "role": "assistant",
                "content": (done["text"] or None) if done else None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"], ensure_ascii=False),
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            yield {"type": "tool_call", "tool": tc["name"], "args": tc["args"], "id": tc["id"]}
            result = await mcp.call(tc["name"], tc["args"])
            yield {"type": "tool_result", "tool": tc["name"], "result": result}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    else:
        yield {
            "type": "error",
            "code": "MAX_TURNS_EXCEEDED",
            "message": f"顾问超出 {MAX_TOOL_TURNS} 轮工具调用上限",
        }

    parsed = _extract_json_object(
        accumulated_text, required_keys=["stance", "confidence", "summary_for_user"]
    )

    if parsed is None:
        logger.warning(
            "顾问 %s 首次未输出合法 JSON；改为只要 JSON 重试一次",
            advisor.profile.name,
        )
        yield {"type": "stage", "stage": "retry_opinion"}

        messages.append(
            {
                "role": "user",
                "content": (
                    "你上一条回复没有以合法的 JSON 对象结尾。请现在**只输出**一个 JSON 对象，"
                    "包含 stance / confidence / summary_for_user / key_points / concerns / "
                    "what_could_change_my_mind 字段。不要任何 markdown 围栏、不要任何前后注释。"
                ),
            }
        )

        retry_text = ""
        async for ev in stream_chat(
            role="advisor",
            model_override=model,
            messages=messages,
            system=composed_system_prompt,
            tools=tool_specs or None,
            max_tokens=2048,
        ):
            if ev["type"] == "text":
                retry_text += ev["chunk"]
            elif ev["type"] == "done":
                tokens_in += ev["tokens_in"]
                tokens_out += ev["tokens_out"]
        parsed = _extract_json_object(
            retry_text, required_keys=["stance", "confidence", "summary_for_user"]
        )

    if parsed is None:
        logger.warning(
            "顾问 %s 重试后仍未输出合法 JSON。原文（最后 1500 字符）：\n%s",
            advisor.profile.name,
            (accumulated_text + "\n--RETRY--\n" + (retry_text if "retry_text" in locals() else ""))[-1500:],
        )
        yield {
            "type": "error",
            "code": "OPINION_PARSE_FAILED",
            "message": "顾问重试后仍未输出合法 JSON",
        }
        yield {"type": "stage", "stage": "done"}
        return

    parsed.setdefault("agent", advisor.profile.name)
    try:
        opinion = AdvisorOpinion.model_validate(parsed)
    except Exception as e:
        yield {
            "type": "error",
            "code": "OPINION_VALIDATION_FAILED",
            "message": f"{type(e).__name__}: {e}",
        }
        yield {"type": "stage", "stage": "done"}
        return

    yield {"type": "opinion", "full": opinion.model_dump()}
    yield {"type": "usage", "tokens_in": tokens_in, "tokens_out": tokens_out}
    yield {"type": "stage", "stage": "done"}

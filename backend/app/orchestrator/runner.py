"""Single-advisor runner: drives one Anthropic Messages tool-use loop and yields stream events."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

from app.config import get_settings
from app.llm.client import get_client
from app.mcp_client.manager import get_manager
from app.orchestrator.advisors.base import BaseAdvisor
from app.orchestrator.protocol import AdvisorOpinion
from app.orchestrator.skills.registry import get_skill_registry

logger = logging.getLogger(__name__)

MAX_TOOL_TURNS = 6


def _extract_json_object(
    text: str, required_keys: list[str] | None = None
) -> dict[str, Any] | None:
    """Extract a JSON object from `text`, tolerating surrounding prose / fences.

    Strategy:
      1. Strip ``` / ```json fences.
      2. Forward-scan to find every top-level (depth-0) balanced `{...}` span.
      3. If `required_keys` is given, prefer the latest span that contains *all* of them
         (this avoids picking nested objects like `{"bullish": [...]}` inside a disagreement).
      4. Fall back to the latest successfully parsed object.
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
                continue  # unbalanced stray; ignore
            depth -= 1
            if depth == 0 and start is not None:
                spans.append((start, i))
                start = None

    if not spans:
        return None

    # First pass: latest span with all required keys
    if required_keys:
        for s, e in reversed(spans):
            try:
                obj = json.loads(stripped[s : e + 1])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and all(k in obj for k in required_keys):
                return obj

    # Fallback: latest parseable object
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
    client: AsyncAnthropic | None = None,
    model: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield stream events for one advisor's full reasoning turn.

    Event types:
      {type: "advisor_start", advisor, display, role, color}
      {type: "text", chunk}                       # streamed text deltas
      {type: "tool_call", tool, args}             # tool use requested by model
      {type: "tool_result", tool, result}         # our handler's reply
      {type: "opinion", full}                     # final structured AdvisorOpinion (dict)
      {type: "stage", stage: "thinking"|"tool_use"|"done"}
      {type: "error", code, message}
    """
    settings = get_settings()
    client = client or get_client()
    model = model or advisor.model or settings.default_advisor_model

    mcp = get_manager()
    tool_specs = mcp.anthropic_specs(advisor.allowed_tools)

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

    for turn in range(MAX_TOOL_TURNS):
        yield {"type": "stage", "stage": "thinking"}

        async with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=composed_system_prompt,
            tools=tool_specs or None,
            messages=messages,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    chunk = event.delta.text
                    accumulated_text += chunk
                    yield {"type": "text", "chunk": chunk}

            final = await stream.get_final_message()

        if final.usage:
            tokens_in += final.usage.input_tokens or 0
            tokens_out += final.usage.output_tokens or 0

        assistant_content = [b.model_dump() for b in final.content]
        messages.append({"role": "assistant", "content": assistant_content})

        if final.stop_reason != "tool_use":
            break

        tool_results: list[dict[str, Any]] = []
        for block in final.content:
            if block.type != "tool_use":
                continue
            yield {
                "type": "tool_call",
                "tool": block.name,
                "args": block.input,
                "id": block.id,
            }
            result = await mcp.call(block.name, block.input)
            yield {"type": "tool_result", "tool": block.name, "result": result}
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

        messages.append({"role": "user", "content": tool_results})
    else:
        yield {
            "type": "error",
            "code": "MAX_TURNS_EXCEEDED",
            "message": f"Advisor exceeded {MAX_TOOL_TURNS} tool turns",
        }

    parsed = _extract_json_object(
        accumulated_text, required_keys=["stance", "confidence", "summary_for_user"]
    )

    if parsed is None:
        logger.warning(
            "Opinion parse failed for %s on first try; asking for JSON only.",
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
        async with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=composed_system_prompt,
            tools=tool_specs or None,
            messages=messages,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    retry_text += event.delta.text
            retry_final = await stream.get_final_message()
        if retry_final.usage:
            tokens_in += retry_final.usage.input_tokens or 0
            tokens_out += retry_final.usage.output_tokens or 0
        parsed = _extract_json_object(
            retry_text, required_keys=["stance", "confidence", "summary_for_user"]
        )

    if parsed is None:
        logger.warning(
            "Opinion parse failed for %s after retry. Raw text (last 1500 chars):\n%s",
            advisor.profile.name,
            (accumulated_text + "\n--RETRY--\n" + (retry_text if "retry_text" in locals() else ""))[-1500:],
        )
        yield {
            "type": "error",
            "code": "OPINION_PARSE_FAILED",
            "message": "Advisor did not produce a valid JSON opinion after retry",
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

"""SSE 聊天端点。支持三种模式：

- `solo`：单顾问（M1 行为，默认明哥）
- `mini`：3 顾问圆桌 + 主持人综合（M2 默认）
- `full`：6 顾问全员 + 主持人综合
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Literal
from uuid import UUID

# 用全局强引用集合保住「发完不等」的后台任务，让它们能跑完。
# Python asyncio 默认对 task 是弱引用 —— 不加这层集合，auto-title 任务可能
# 在生成器结束时就被 GC 回收掉。
_BACKGROUND_TASKS: set[asyncio.Task] = set()

from anthropic import APIStatusError
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.db.repository import (
    create_conversation,
    get_conversation,
    get_or_create_demo_member,
    save_message,
)
from app.db.session import SessionLocal
from app.orchestrator.advisors import get_advisor, get_full_council, get_mini_council
from app.orchestrator.conductor import run_council
from app.orchestrator.runner import run_advisor
from app.orchestrator.titler import auto_title

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)

Mode = Literal["solo", "mini", "full"]


class ChatRequest(BaseModel):
    question: str
    mode: Mode = "mini"
    advisor: str = "ming_ge"  # 仅在 mode=solo 时生效
    conversation_id: UUID | None = None


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


class _AdvisorAccum:
    """单顾问累计器：圆桌结束时用它持久化一条 `advisor:<name>` 消息。"""

    def __init__(self, name: str, model: str) -> None:
        self.name = name
        self.model = model
        self.text = ""
        self.tool_calls: list[dict] = []
        self.opinion: dict | None = None
        self.active_skills: list[str] = []
        self.tokens_in: int = 0
        self.tokens_out: int = 0


async def _stream(req: ChatRequest) -> AsyncIterator[str]:
    settings = get_settings()

    if req.mode == "solo":
        advisor = get_advisor(req.advisor)
        if advisor is None:
            yield _sse({"type": "error", "code": "UNKNOWN_ADVISOR", "message": req.advisor})
            return
        advisors = [advisor]
        mode_tag = f"solo:{advisor.profile.name}"
    elif req.mode == "full":
        advisors = get_full_council()
        mode_tag = "full"
    else:
        advisors = get_mini_council()
        mode_tag = "mini"

    async with SessionLocal() as db:
        try:
            member = await get_or_create_demo_member(db)
            is_new_conv = req.conversation_id is None
            if req.conversation_id:
                conv = await get_conversation(db, req.conversation_id)
                if conv is None or conv.member_id != member.id:
                    yield _sse(
                        {
                            "type": "error",
                            "code": "CONVERSATION_NOT_FOUND",
                            "message": str(req.conversation_id),
                        }
                    )
                    return
            else:
                conv = await create_conversation(
                    db, member=member, mode=mode_tag, first_question=req.question
                )

            yield _sse(
                {"type": "session", "conversation_id": str(conv.id), "title": conv.title, "mode": conv.mode}
            )
            await save_message(db, conversation=conv, role="user", content=req.question)
        except Exception as e:
            logger.exception("chat init failed")
            yield _sse({"type": "error", "code": "INIT_FAILED", "message": f"{type(e).__name__}: {e}"})
            return

        accums: dict[str, _AdvisorAccum] = {
            a.profile.name: _AdvisorAccum(
                a.profile.name, a.model or settings.default_advisor_model
            )
            for a in advisors
        }
        synthesis_text = ""
        synthesis_full: dict | None = None
        nonlocal_synthesis_tokens: dict[str, int] = {"in": 0, "out": 0}

        try:
            if req.mode == "solo":
                event_iter = run_advisor(advisors[0], req.question)
            else:
                event_iter = run_council(advisors, req.question)

            async for event in event_iter:
                etype = event.get("type")
                advisor_name = event.get("advisor")

                # solo 模式下 run_advisor 不会给事件挂 advisor 字段，这里补一个默认
                if advisor_name is None and req.mode == "solo":
                    advisor_name = advisors[0].profile.name

                if advisor_name and advisor_name in accums:
                    acc = accums[advisor_name]
                    if etype == "advisor_start":
                        acc.active_skills = event.get("active_skills", []) or []
                    elif etype == "text":
                        acc.text += event.get("chunk", "")
                    elif etype == "tool_call":
                        acc.tool_calls.append(
                            {
                                "id": event.get("id"),
                                "tool": event.get("tool"),
                                "args": event.get("args"),
                            }
                        )
                    elif etype == "tool_result":
                        for tc in reversed(acc.tool_calls):
                            if tc.get("tool") == event.get("tool") and "result" not in tc:
                                tc["result"] = event.get("result")
                                break
                    elif etype == "opinion":
                        acc.opinion = event.get("full")
                    elif etype == "usage":
                        acc.tokens_in = event.get("tokens_in", 0)
                        acc.tokens_out = event.get("tokens_out", 0)

                if etype == "synthesis_text":
                    synthesis_text += event.get("chunk", "")
                elif etype == "synthesis":
                    synthesis_full = event.get("full")
                elif etype == "synthesis_usage":
                    nonlocal_synthesis_tokens["in"] = event.get("tokens_in", 0)
                    nonlocal_synthesis_tokens["out"] = event.get("tokens_out", 0)

                yield _sse(event)

            # 持久化：每位顾问一条；圆桌模式下额外加一条 conductor
            for acc in accums.values():
                if not acc.text and acc.opinion is None and not acc.tool_calls:
                    continue
                await save_message(
                    db,
                    conversation=conv,
                    role=f"advisor:{acc.name}",
                    agent=acc.name,
                    content=acc.text,
                    structured=acc.opinion,
                    tool_calls=acc.tool_calls,
                    active_skills=acc.active_skills,
                    model=acc.model,
                    tokens_in=acc.tokens_in or None,
                    tokens_out=acc.tokens_out or None,
                )

            if req.mode in ("mini", "full") and (synthesis_text or synthesis_full):
                await save_message(
                    db,
                    conversation=conv,
                    role="conductor",
                    agent="zhi_qi",
                    content=synthesis_text,
                    structured=synthesis_full,
                    tool_calls=[],
                    model=settings.conductor_model,
                    tokens_in=nonlocal_synthesis_tokens["in"] or None,
                    tokens_out=nonlocal_synthesis_tokens["out"] or None,
                )

            # 后台任务：为新建会话自动生成标题
            if is_new_conv:
                hint: str | None = None
                if synthesis_full and synthesis_full.get("final_summary"):
                    hint = synthesis_full["final_summary"]
                else:
                    for acc in accums.values():
                        if acc.opinion and acc.opinion.get("summary_for_user"):
                            hint = acc.opinion["summary_for_user"]
                            break
                logger.warning("scheduling auto_title for new conv %s hint=%r", conv.id, hint[:40] if hint else None)
                task = asyncio.create_task(auto_title(conv.id, req.question, hint))
                _BACKGROUND_TASKS.add(task)
                task.add_done_callback(_BACKGROUND_TASKS.discard)
        except APIStatusError as e:
            logger.exception("relay/Anthropic API error")
            yield _sse(_relay_error_event(e))
        except Exception as e:
            logger.exception("chat stream failed")
            yield _sse({"type": "error", "code": "INTERNAL", "message": f"{type(e).__name__}: {e}"})


def _relay_error_event(e: APIStatusError) -> dict:
    """把 Anthropic SDK 抛的 API 错误转成对用户友好的 SSE 错误事件。"""
    status = getattr(e, "status_code", None)
    body = getattr(e, "body", None) or {}
    inner = (body.get("error") if isinstance(body, dict) else None) or {}
    msg = (inner.get("message") if isinstance(inner, dict) else None) or str(e)

    if status == 402:
        return {
            "type": "error",
            "code": "RELAY_INSUFFICIENT_BALANCE",
            "message": "中转账户余额不足，请去 matrix-net.tech 充值",
            "detail": msg,
        }
    if status == 401:
        return {
            "type": "error",
            "code": "RELAY_AUTH_FAILED",
            "message": "中转 API Key 无效或已过期，请检查 RELAY_API_KEY",
            "detail": msg,
        }
    if status == 429:
        return {
            "type": "error",
            "code": "RELAY_RATE_LIMITED",
            "message": "中转请求频率超限，请稍后再试",
            "detail": msg,
        }
    return {
        "type": "error",
        "code": f"RELAY_HTTP_{status or 'UNKNOWN'}",
        "message": msg or "中转请求失败",
        "detail": str(e)[:300],
    }


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

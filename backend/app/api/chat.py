"""SSE chat endpoint. Supports two modes:

- `solo`: single advisor (M1 behaviour, defaults to ming_ge)
- `mini`: 3-advisor mini council + conductor synthesis (M2 default)
"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Literal
from uuid import UUID

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

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)

Mode = Literal["solo", "mini", "full"]


class ChatRequest(BaseModel):
    question: str
    mode: Mode = "mini"
    advisor: str = "ming_ge"  # only used when mode=solo
    conversation_id: UUID | None = None


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


class _AdvisorAccum:
    """Per-advisor accumulator used to persist a `advisor:<name>` message at council end."""

    def __init__(self, name: str, model: str) -> None:
        self.name = name
        self.model = model
        self.text = ""
        self.tool_calls: list[dict] = []
        self.opinion: dict | None = None
        self.active_skills: list[str] = []


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

        try:
            if req.mode == "solo":
                event_iter = run_advisor(advisors[0], req.question)
            else:
                event_iter = run_council(advisors, req.question)

            async for event in event_iter:
                etype = event.get("type")
                advisor_name = event.get("advisor")

                # For solo mode, run_advisor doesn't tag events with `advisor`, so default it
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

                if etype == "synthesis_text":
                    synthesis_text += event.get("chunk", "")
                elif etype == "synthesis":
                    synthesis_full = event.get("full")

                yield _sse(event)

            # Persist: one row per advisor + one row for the conductor (if council mode)
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
                )
        except Exception as e:
            logger.exception("chat stream failed")
            yield _sse({"type": "error", "code": "INTERNAL", "message": f"{type(e).__name__}: {e}"})


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

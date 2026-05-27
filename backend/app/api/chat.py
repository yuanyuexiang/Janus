"""SSE chat endpoint. Persists conversations + messages to Postgres."""

import json
import logging
from collections.abc import AsyncIterator
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
from app.orchestrator.advisors.ming_ge import ALL_ADVISORS
from app.orchestrator.runner import run_advisor

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str
    advisor: str = "ming_ge"
    conversation_id: UUID | None = None


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def _stream(req: ChatRequest) -> AsyncIterator[str]:
    advisor = ALL_ADVISORS.get(req.advisor)
    if advisor is None:
        yield _sse({"type": "error", "code": "UNKNOWN_ADVISOR", "message": req.advisor})
        return

    settings = get_settings()
    model = advisor.model or settings.default_advisor_model

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
                    db, member=member, mode=f"solo:{advisor.profile.name}",
                    first_question=req.question,
                )

            yield _sse({"type": "session", "conversation_id": str(conv.id), "title": conv.title})

            await save_message(db, conversation=conv, role="user", content=req.question)
        except Exception as e:
            logger.exception("chat init failed")
            yield _sse({"type": "error", "code": "INIT_FAILED", "message": f"{type(e).__name__}: {e}"})
            return

        accumulated_text = ""
        tool_calls: list[dict] = []
        opinion: dict | None = None

        try:
            async for event in run_advisor(advisor, req.question):
                etype = event.get("type")
                if etype == "text":
                    accumulated_text += event.get("chunk", "")
                elif etype == "tool_call":
                    tool_calls.append(
                        {
                            "id": event.get("id"),
                            "tool": event.get("tool"),
                            "args": event.get("args"),
                        }
                    )
                elif etype == "tool_result":
                    for tc in reversed(tool_calls):
                        if tc.get("tool") == event.get("tool") and "result" not in tc:
                            tc["result"] = event.get("result")
                            break
                elif etype == "opinion":
                    opinion = event.get("full")
                yield _sse(event)

            await save_message(
                db,
                conversation=conv,
                role=f"advisor:{advisor.profile.name}",
                agent=advisor.profile.name,
                content=accumulated_text,
                structured=opinion,
                tool_calls=tool_calls,
                model=model,
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

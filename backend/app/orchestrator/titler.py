"""Auto-title a freshly created conversation.

Heuristic: when the first opinion/synthesis lands, ask the model for a short
Chinese title (8-15 chars) and PATCH `conversations.title`. Runs as a background
asyncio task so it does not block the SSE stream the user is watching.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.config import get_settings
from app.db.repository import get_conversation, update_conversation_title
from app.db.session import SessionLocal
from app.llm.client import get_client

logger = logging.getLogger(__name__)


TITLER_SYSTEM = (
    "你是一名严谨的标题编辑。任务：为投资讨论会话生成一个简短中文标题。\n"
    "约束：\n"
    "- 8-15 个汉字\n"
    "- 包含核心标的或主题（如「茅台估值」「半导体景气」「全球宏观展望」）\n"
    "- 不使用引号、句号、问号\n"
    "- 直接输出标题文本，不要任何前后注释、不要 markdown 围栏"
)


async def generate_title(question: str, summary_hint: str | None = None) -> str | None:
    settings = get_settings()
    if not settings.relay_base_url or not settings.relay_api_key:
        return None
    client = get_client()
    parts = [f"用户提问：\n{question}"]
    if summary_hint:
        parts.append(f"\n首位顾问的总结要点：\n{summary_hint[:400]}")
    parts.append("\n请输出标题（仅文本本身）：")
    user_msg = "\n".join(parts)

    try:
        resp = await client.messages.create(
            model=settings.router_model,
            max_tokens=64,
            system=TITLER_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        logger.warning("titler LLM call failed: %s", e)
        return None

    raw = ""
    for block in resp.content:
        if block.type == "text":
            raw += block.text
    logger.warning("titler raw response: %r", raw[:200])
    text = raw.strip()
    if not text:
        return None
    # Take first non-empty line, strip surrounding punctuation
    text = text.splitlines()[0].strip().strip("「」\"'。？！. ")
    # Sanity: 4-30 chars after cleanup
    if not (4 <= len(text) <= 30):
        logger.warning("titler rejected length=%d text=%r", len(text), text)
        return None
    return text


async def auto_title(conv_id: UUID, question: str, summary_hint: str | None = None) -> None:
    """Background task: generate title and persist. Logs+swallows all errors."""
    logger.warning("auto_title task running for %s", conv_id)
    try:
        title = await generate_title(question, summary_hint)
        logger.warning("auto_title generated %r for %s", title, conv_id)
        if not title:
            return
        async with SessionLocal() as db:
            conv = await get_conversation(db, conv_id)
            if conv is None:
                logger.warning("auto_title: conv %s vanished", conv_id)
                return
            await update_conversation_title(db, conv, title=title)
            logger.warning("auto-titled %s → %s", conv_id, title)
    except Exception:
        logger.exception("auto_title failed for %s", conv_id)

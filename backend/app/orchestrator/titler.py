"""会话自动标题。

启发式：首轮 opinion / synthesis 落地后，调一次 LLM 生成简短中文标题，
然后 PATCH 到 `conversations.title`。作为后台 asyncio 任务跑，不阻塞用户看的 SSE 流。
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.db.repository import get_conversation, update_conversation_title
from app.db.session import SessionLocal
from app.llm.client import complete, is_configured

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
    if not is_configured("router"):  # 标题用 router 角色，没配就跳过
        return None
    parts = [f"用户提问：\n{question}"]
    if summary_hint:
        parts.append(f"\n首位顾问的总结要点：\n{summary_hint[:400]}")
    parts.append("\n请输出标题（仅文本本身）：")
    user_msg = "\n".join(parts)

    try:
        raw, _usage = await complete(
            role="router",
            messages=[{"role": "user", "content": user_msg}],
            system=TITLER_SYSTEM,
            max_tokens=64,
        )
    except Exception as e:
        logger.warning("titler LLM 调用失败: %s", e)
        return None

    logger.warning("titler 原始返回: %r", raw[:200])
    text = raw.strip()
    if not text:
        return None
    # 取第一段非空行，剥掉前后的引号 / 标点
    text = text.splitlines()[0].strip().strip("「」\"'。？！. ")
    # 健康检查：清理后长度 4-30 字符
    if not (4 <= len(text) <= 30):
        logger.warning("titler 标题被拒：长度 %d，内容 %r", len(text), text)
        return None
    return text


async def auto_title(conv_id: UUID, question: str, summary_hint: str | None = None) -> None:
    """后台任务：生成标题并写库。任何异常都吞掉只记日志。"""
    logger.warning("auto_title 任务启动：会话 %s", conv_id)
    try:
        title = await generate_title(question, summary_hint)
        logger.warning("auto_title 已生成 %r（会话 %s）", title, conv_id)
        if not title:
            return
        async with SessionLocal() as db:
            conv = await get_conversation(db, conv_id)
            if conv is None:
                logger.warning("auto_title：会话 %s 已不存在", conv_id)
                return
            await update_conversation_title(db, conv, title=title)
            logger.warning("auto_title 已写入 %s → %s", conv_id, title)
    except Exception:
        logger.exception("auto_title 失败：会话 %s", conv_id)

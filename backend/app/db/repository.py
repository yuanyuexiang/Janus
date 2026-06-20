"""会话持久化的仓储层 helper。MVP 阶段只用一个 demo member。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, LlmSetting, Member, Message

DEMO_MEMBER_EMAIL = "demo@yuanzhuo.local"
DEMO_MEMBER_NAME = "Demo Member"


# ---------- LLM 配置 ----------


async def get_llm_settings(db: AsyncSession) -> list[LlmSetting]:
    res = await db.execute(select(LlmSetting))
    return list(res.scalars().all())


async def upsert_llm_setting(
    db: AsyncSession,
    *,
    role: str,
    model: str | None,
    api_base: str | None,
    api_key_enc: str | None,
) -> LlmSetting:
    """新增/更新某角色配置。api_key_enc=None 表示「不动已存的 key」。"""
    obj = await db.get(LlmSetting, role)
    if obj is None:
        obj = LlmSetting(role=role)
        db.add(obj)
    obj.model = model
    obj.api_base = api_base
    if api_key_enc is not None:
        obj.api_key_enc = api_key_enc
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_or_create_demo_member(db: AsyncSession) -> Member:
    stmt = select(Member).where(Member.email == DEMO_MEMBER_EMAIL)
    member = (await db.execute(stmt)).scalar_one_or_none()
    if member is None:
        member = Member(display_name=DEMO_MEMBER_NAME, email=DEMO_MEMBER_EMAIL)
        db.add(member)
        await db.commit()
        await db.refresh(member)
    return member


async def get_conversation(db: AsyncSession, conv_id: UUID) -> Conversation | None:
    return (
        await db.execute(select(Conversation).where(Conversation.id == conv_id))
    ).scalar_one_or_none()


async def create_conversation(
    db: AsyncSession, *, member: Member, mode: str, first_question: str
) -> Conversation:
    title = first_question.strip().splitlines()[0][:80]
    conv = Conversation(member_id=member.id, mode=mode, title=title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def save_message(
    db: AsyncSession,
    *,
    conversation: Conversation,
    role: str,
    content: str | None,
    agent: str | None = None,
    structured: dict | None = None,
    tool_calls: list | None = None,
    active_skills: list | None = None,
    model: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation.id,
        role=role,
        agent=agent,
        content=content,
        structured=structured,
        tool_calls=tool_calls or [],
        active_skills=active_skills or [],
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def list_conversations(db: AsyncSession, member: Member, limit: int = 50) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.member_id == member.id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def update_conversation_title(
    db: AsyncSession, conv: Conversation, *, title: str
) -> Conversation:
    conv.title = title.strip()[:128]
    await db.commit()
    await db.refresh(conv)
    return conv


async def delete_conversation(db: AsyncSession, conv: Conversation) -> None:
    await db.delete(conv)
    await db.commit()


async def list_messages(db: AsyncSession, conv_id: UUID) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())

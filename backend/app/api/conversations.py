"""Conversation list + detail endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import (
    get_conversation,
    get_or_create_demo_member,
    list_conversations,
    list_messages,
)
from app.db.session import get_db

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationSummary(BaseModel):
    id: UUID
    title: str | None
    mode: str | None
    created_at: datetime
    updated_at: datetime


class MessageItem(BaseModel):
    id: int
    role: str
    agent: str | None
    content: str | None
    structured: dict | None
    tool_calls: list
    model: str | None
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageItem]


@router.get("", response_model=list[ConversationSummary])
async def list_all(db: AsyncSession = Depends(get_db)) -> list[ConversationSummary]:
    member = await get_or_create_demo_member(db)
    rows = await list_conversations(db, member)
    return [
        ConversationSummary(
            id=c.id, title=c.title, mode=c.mode, created_at=c.created_at, updated_at=c.updated_at
        )
        for c in rows
    ]


@router.get("/{conv_id}", response_model=ConversationDetail)
async def get_one(conv_id: UUID, db: AsyncSession = Depends(get_db)) -> ConversationDetail:
    member = await get_or_create_demo_member(db)
    conv = await get_conversation(db, conv_id)
    if conv is None or conv.member_id != member.id:
        raise HTTPException(404, "conversation not found")

    msgs = await list_messages(db, conv_id)
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        mode=conv.mode,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageItem(
                id=m.id,
                role=m.role,
                agent=m.agent,
                content=m.content,
                structured=m.structured,
                tool_calls=m.tool_calls or [],
                model=m.model,
                created_at=m.created_at,
            )
            for m in msgs
        ],
    )

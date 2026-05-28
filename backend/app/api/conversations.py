"""Conversation list / detail / patch / delete / export."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import (
    delete_conversation,
    get_conversation,
    get_or_create_demo_member,
    list_conversations,
    list_messages,
    update_conversation_title,
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
    active_skills: list
    model: str | None
    tokens_in: int | None
    tokens_out: int | None
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageItem]


class ConversationPatch(BaseModel):
    title: str = Field(min_length=1, max_length=128)


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
                active_skills=m.active_skills or [],
                model=m.model,
                tokens_in=m.tokens_in,
                tokens_out=m.tokens_out,
                created_at=m.created_at,
            )
            for m in msgs
        ],
    )


@router.patch("/{conv_id}", response_model=ConversationSummary)
async def patch_one(
    conv_id: UUID, body: ConversationPatch, db: AsyncSession = Depends(get_db)
) -> ConversationSummary:
    member = await get_or_create_demo_member(db)
    conv = await get_conversation(db, conv_id)
    if conv is None or conv.member_id != member.id:
        raise HTTPException(404, "conversation not found")
    updated = await update_conversation_title(db, conv, title=body.title)
    return ConversationSummary(
        id=updated.id,
        title=updated.title,
        mode=updated.mode,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/{conv_id}", status_code=204)
async def delete_one(conv_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    member = await get_or_create_demo_member(db)
    conv = await get_conversation(db, conv_id)
    if conv is None or conv.member_id != member.id:
        raise HTTPException(404, "conversation not found")
    await delete_conversation(db, conv)
    return Response(status_code=204)


# ----------------------------- Export -----------------------------

ADVISOR_DISPLAY = {
    "tao_shu": ("韬叔", "宏观"),
    "lan_jie": ("岚姐", "行业"),
    "ming_ge": ("明哥", "价值"),
    "rui_feng": ("锐锋", "趋势"),
    "leng_chuan": ("冷川", "风险"),
    "ling_du": ("零度", "量化"),
}


def _render_markdown(detail: ConversationDetail) -> str:
    lines: list[str] = []
    lines.append(f"# {detail.title or '(无标题)'}")
    lines.append("")
    lines.append(f"- **模式**: `{detail.mode or '-'}`")
    lines.append(f"- **创建**: {detail.created_at.isoformat()}")
    lines.append(f"- **更新**: {detail.updated_at.isoformat()}")
    lines.append(f"- **消息数**: {len(detail.messages)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for m in detail.messages:
        if m.role == "user":
            lines.append("## 🙋 用户")
            lines.append("")
            lines.append(m.content or "")
            lines.append("")
        elif m.role.startswith("advisor:"):
            name = m.agent or m.role.split(":", 1)[1]
            display, role_label = ADVISOR_DISPLAY.get(name, (name, ""))
            lines.append(f"## 🧑‍💼 {display}（{role_label}）")
            lines.append("")
            if m.active_skills:
                lines.append(f"**Active Skills**: {', '.join(f'`{s}`' for s in m.active_skills)}")
                lines.append("")
            if m.tool_calls:
                lines.append("**工具调用**：")
                for tc in m.tool_calls:
                    args = tc.get("args")
                    lines.append(f"- `{tc.get('tool')}({args})`")
                lines.append("")
            if m.structured:
                s = m.structured
                lines.append(f"**立场**: `{s.get('stance')}`  ·  **置信度**: {s.get('confidence')}")
                lines.append("")
                lines.append(f"> {s.get('summary_for_user', '')}")
                lines.append("")
                if s.get("key_points"):
                    lines.append("**核心观点**：")
                    for p in s["key_points"]:
                        src = f" _(source: {p['source_tool']})_" if p.get("source_tool") else ""
                        lines.append(f"- **{p.get('claim', '')}**{src}")
                        if p.get("detail"):
                            lines.append(f"  - {p['detail']}")
                    lines.append("")
                if s.get("concerns"):
                    lines.append("**主要风险**：")
                    for c in s["concerns"]:
                        lines.append(f"- {c}")
                    lines.append("")
                if s.get("what_could_change_my_mind"):
                    lines.append("**变心条件**：")
                    for c in s["what_could_change_my_mind"]:
                        lines.append(f"- {c}")
                    lines.append("")
        elif m.role == "conductor":
            lines.append("## 🎩 执棋（主持人 · 综合）")
            lines.append("")
            if m.structured:
                s = m.structured
                lines.append(f"**判定**: `{s.get('verdict')}`")
                lines.append("")
                lines.append(f"> {s.get('final_summary', '')}")
                lines.append("")
                if s.get("consensus"):
                    lines.append("**共识**：")
                    for c in s["consensus"]:
                        lines.append(f"- {c}")
                    lines.append("")
                if s.get("disagreements"):
                    lines.append("**分歧**：")
                    for d in s["disagreements"]:
                        lines.append(f"- **{d.get('point', '')}**")
                        for stance, sides in (d.get("sides") or {}).items():
                            lines.append(f"  - _{stance}_:")
                            for a in sides:
                                lines.append(f"    - {a}")
                    lines.append("")
                if s.get("key_variables"):
                    lines.append("**关键变量**：")
                    for v in s["key_variables"]:
                        lines.append(f"- {v}")
                    lines.append("")
                if s.get("risk_map"):
                    lines.append("**风险地图**：")
                    for r in s["risk_map"]:
                        sev = r.get("severity", "?")
                        lines.append(f"- **[严重度 {sev}/5]** {r.get('risk', '')}")
                        if r.get("mitigation"):
                            lines.append(f"  - 缓释：{r['mitigation']}")
                    lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("")
    lines.append(f"_导出于 {datetime.utcnow().isoformat()}Z · 圆桌投研_")
    return "\n".join(lines)


@router.get("/{conv_id}/export")
async def export_one(
    conv_id: UUID,
    format: Literal["md", "json"] = Query(default="md"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    detail = await get_one(conv_id, db)
    if format == "json":
        return Response(
            content=detail.model_dump_json(indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="conversation-{conv_id}.json"'
            },
        )
    md = _render_markdown(detail)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="conversation-{conv_id}.md"'
        },
    )

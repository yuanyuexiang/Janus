from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSONB, list: JSONB}


class Member(Base):
    __tablename__ = "members"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    display_name: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolios: Mapped[list["PortfolioSnapshot"]] = relationship(back_populates="member")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="member")


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    member_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE")
    )
    as_of_date: Mapped[date] = mapped_column(Date)
    positions: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped[Member] = relationship(back_populates="portfolios")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    member_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("members.id", ondelete="SET NULL")
    )
    title: Mapped[str | None] = mapped_column(String(128))
    mode: Mapped[str | None] = mapped_column(String(16))  # full / mini / solo:<name>
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    member: Mapped[Member | None] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(32))  # user / advisor:<name> / conductor / system
    agent: Mapped[str | None] = mapped_column(String(32))
    content: Mapped[str | None] = mapped_column(Text)
    structured: Mapped[dict | None] = mapped_column(JSONB)
    tool_calls: Mapped[list] = mapped_column(JSONB, default=list)
    active_skills: Mapped[list] = mapped_column(JSONB, default=list)
    model: Mapped[str | None] = mapped_column(String(64))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

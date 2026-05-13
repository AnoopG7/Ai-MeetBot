from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class SessionLog(Base):
    __tablename__ = "session_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room = Column(String(255), nullable=False)
    participant = Column(String(255), nullable=False)
    user_query = Column(Text, nullable=True)
    agent_response = Column(Text, nullable=True)
    tools_used = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_session_logs_participant", "participant"),
        Index("ix_session_logs_room", "room"),
    )


class UserMemory(Base):
    __tablename__ = "user_memories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    risk_profile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    goals: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    mentioned_products: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    topics: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_interaction: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

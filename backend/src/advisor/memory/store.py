from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from ..core.database import async_session_factory
from ..core.logging import get_logger
from ..core.models import SessionLog, UserMemory

logger = get_logger(__name__)


async def get_user_memory(user_id: str) -> dict[str, Any] | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(UserMemory).where(UserMemory.user_id == user_id)
        )
        mem = result.scalar_one_or_none()
        if mem is None:
            return None
        return {
            "risk_profile": mem.risk_profile,
            "goals": mem.goals or [],
            "mentioned_products": mem.mentioned_products or [],
            "topics": mem.topics or [],
            "bio": mem.bio,
            "conversation_count": mem.conversation_count,
        }


async def upsert_user_memory(
    user_id: str,
    *,
    risk_profile: str | None = None,
    goals: list[str] | None = None,
    mentioned_products: list[str] | None = None,
    topics: list[str] | None = None,
    bio: str | None = None,
) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(UserMemory).where(UserMemory.user_id == user_id)
        )
        mem = result.scalar_one_or_none()

        if mem is None:
            mem = UserMemory(
                user_id=user_id,
                risk_profile=risk_profile,
                goals=goals or [],
                mentioned_products=mentioned_products or [],
                topics=topics or [],
                bio=bio,
                conversation_count=1,
                last_interaction=datetime.now(tz=UTC),
            )
            session.add(mem)
        else:
            for key, val in [
                ("risk_profile", risk_profile),
                ("goals", goals),
                ("mentioned_products", mentioned_products),
                ("topics", topics),
                ("bio", bio),
            ]:
                if val is not None:
                    setattr(mem, key, val)
            mem.conversation_count = UserMemory.conversation_count + 1
            mem.last_interaction = datetime.now(tz=UTC)

        await session.commit()
        logger.debug("user memory updated", user_id=user_id)


async def record_interaction(
    *,
    room: str,
    participant: str,
    user_query: str | None = None,
    agent_response: str | None = None,
    tools_used: list[str] | None = None,
    latency_ms: float | None = None,
) -> str:
    async with async_session_factory() as session:
        log = SessionLog(
            room=room,
            participant=participant,
            user_query=user_query,
            agent_response=agent_response,
            tools_used=tools_used,
            latency_ms=latency_ms,
        )
        session.add(log)
        await session.commit()
        logger.debug("interaction logged", room=room, participant=participant)
        return str(log.id)


async def get_recent_conversations(
    user_id: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(SessionLog)
            .where(SessionLog.participant == user_id)
            .where(SessionLog.user_query.isnot(None))
            .order_by(SessionLog.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        conversations = []
        for row in reversed(rows):
            conversations.append(
                {
                    "user_query": row.user_query or "",
                    "agent_response": row.agent_response or "",
                }
            )
        return conversations

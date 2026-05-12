from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=settings.echo_sql,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    from .models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database tables created")

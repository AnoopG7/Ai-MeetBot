from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import settings
from ..core.logging import configure_logging, get_logger
from .routes import auth, chat_debug, health, token

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    logger.info("starting up", app=settings.app_name, version=settings.app_version)
    try:
        from ..core.database import init_db

        await init_db()
        logger.info("database tables synced")
    except Exception:
        logger.warning("database not available — continuing without DB")
    yield
    logger.info("shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(token.router)
    app.include_router(auth.router)
    app.include_router(chat_debug.router)

    return app


app = create_app()

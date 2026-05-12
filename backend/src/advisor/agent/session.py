from __future__ import annotations

import asyncio
from typing import Any

from livekit.agents import Agent, AgentSession, JobContext
from livekit.plugins import cartesia

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

WELCOME_MESSAGE = (
    "Hello! I'm your personal finance advisor. "
    "I can help you with investments, savings, insurance, taxes, and more. "
    "How can I assist you today?"
)

_DISCLAIMER = (
    "Please remember, I am an AI assistant and not a SEBI-registered financial advisor. "
    "The information I provide is for educational purposes only "
    "and should not be considered as professional financial advice."
)


def create_session(*, voice_id: str | None = None) -> AgentSession[Any]:
    tts = cartesia.TTS(
        model="sonic-3",
        voice=voice_id or settings.cartesia_voice_id,
        speed=1.0,
        api_key=settings.cartesia_api_key,
    )

    return AgentSession(
        tts=tts,
        # STT, VAD, LLM — added in Phases 3-5
    )


def create_agent() -> Agent:
    return Agent(
        instructions=(
            "You are a helpful and knowledgeable personal finance advisor for Indian users. "
            "You provide clear, accurate, and responsible financial guidance.\n\n"
            "Guidelines:\n"
            "- Always respond in clear English (Indian English preferred).\n"
            "- Never give stock tips or guaranteed returns.\n"
            "- Always include a disclaimer about consulting a SEBI-registered advisor.\n"
            "- Be friendly, patient, and educational.\n"
            "- Avoid jargon unless you explain it."
        ),
    )


async def run_agent(ctx: JobContext) -> None:
    participant = await ctx.wait_for_participant()
    logger.info(
        "agent session started",
        room=ctx.room.name,
        participant=participant.identity,
    )

    session = create_session()
    agent = create_agent()

    await session.start(agent=agent, room=ctx.room)

    session.say(WELCOME_MESSAGE)
    session.say(_DISCLAIMER, allow_interruptions=False)

    await asyncio.Event().wait()

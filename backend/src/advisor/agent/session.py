from __future__ import annotations

import asyncio
from typing import Any

from livekit.agents import Agent, AgentSession, JobContext
from livekit.plugins import cartesia, deepgram, openai

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

_FINANCE_KEYWORDS = [
    ("SIP", 2.0),
    ("PPF", 2.0),
    ("NPS", 2.0),
    ("ELSS", 2.0),
    ("CIBIL", 2.0),
    ("KYC", 2.0),
    ("FD", 1.5),
    ("RD", 1.5),
    ("EMI", 1.5),
    ("TDS", 1.5),
    ("GST", 1.5),
    ("ITR", 1.5),
    ("PAN", 1.5),
    ("Aadhaar", 1.5),
]


def create_stt() -> deepgram.STT:
    api_key = settings.deepgram_api_key
    if not api_key:
        logger.warning("DEEPGRAM_API_KEY not set — STT will fail at runtime")

    return deepgram.STT(
        model="nova-3",
        language="en-IN",
        detect_language=False,
        smart_format=True,
        punctuate=True,
        interim_results=True,
        filler_words=True,
        keywords=_FINANCE_KEYWORDS,
        api_key=api_key,
    )


def create_llm() -> openai.LLM:
    if settings.llm_provider == "ollama":
        if not settings.ollama_base_url:
            logger.warning("OLLAMA_BASE_URL not set — LLM will fail at runtime")
        return openai.LLM(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            api_key="ollama",
        )

    api_key = settings.openai_api_key
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — LLM will fail at runtime")
    return openai.LLM(
        model=settings.openai_model,
        api_key=api_key,
    )


def create_session(
    *,
    vad_model: Any | None = None,
    voice_id: str | None = None,
) -> AgentSession[Any]:
    cartesia_key = settings.cartesia_api_key
    if not cartesia_key:
        logger.warning("CARTESIA_API_KEY not set — TTS will fail at runtime")

    tts = cartesia.TTS(
        model="sonic-3",
        voice=voice_id or settings.cartesia_voice_id,
        speed=1.0,
        api_key=cartesia_key,
    )

    stt = create_stt()

    kwargs: dict[str, Any] = dict(
        tts=tts,
        stt=stt,
    )

    if vad_model is not None:
        kwargs["vad"] = vad_model

    llm = create_llm()
    kwargs["llm"] = llm

    return AgentSession(**kwargs)


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

    vad = ctx.proc.userdata.get("vad")
    session = create_session(vad_model=vad)
    agent = create_agent()

    await session.start(agent=agent, room=ctx.room)

    session.say(WELCOME_MESSAGE)
    session.say(_DISCLAIMER, allow_interruptions=False)

    await asyncio.Event().wait()

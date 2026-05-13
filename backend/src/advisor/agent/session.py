from __future__ import annotations

import asyncio
from typing import Any

from livekit.agents import Agent, AgentSession, JobContext
from livekit.plugins import deepgram, openai, cartesia

from ..core.config import settings
from ..core.logging import get_logger
from ..memory import (
    get_recent_conversations,
    get_user_memory,
    record_interaction,
    upsert_user_memory,
)
from ..vision.state import state_store as visual_state_store
from .tools import FINANCE_TOOLS
from .tts_edge import EdgeTTS
from .stt_faster_whisper import FasterWhisperSTT

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

_BASE_INSTRUCTIONS = (
    "You are a knowledgeable personal finance advisor for Indian users. "
    "You provide clear, accurate, and responsible financial guidance.\n\n"
    "Guidelines:\n"
    "- Always respond in clear English (Indian English preferred).\n"
    "- Never give stock tips, guaranteed returns, or specific stock recommendations.\n"
    "- Always include a disclaimer about consulting a SEBI-registered advisor "
    "for personalized advice.\n"
    "- Be friendly, patient, and educational.\n"
    "- Avoid jargon unless you explain it.\n"
    "- When the user asks about financial products, tax rules, or regulations, "
     "use lookup_finance_knowledge to get accurate information. "
     "Call the tool ONCE per distinct query, not repeatedly.\n"
     "- When citing information from lookup_finance_knowledge, mention "
     "the source in your response.\n"
    "- Use calculate_emi for loan EMI queries.\n"
    "- Use calculate_sip_returns for investment return projections.\n"
    "- Use assess_risk_profile to help users understand their risk tolerance.\n"
     "- Use escalate_to_human when the user explicitly asks for a human advisor.\n"
     "- Use get_visual_context to check user engagement, gaze, and head pose. "
     "Call this when the user seems distracted or when you need to adapt your response.\n\n"
    "Use case detection - Identify the user's primary need:\n"
    "- Investments / Mutual Funds / SIP\n"
    "- Tax Planning / ITR / Deductions\n"
    "- Loans / EMI / CIBIL / Credit\n"
    "- Insurance (term, health, life)\n"
    "- Retirement (PPF, NPS, pension)\n"
    "- Savings (FD, RD, savings account)\n"
    "- General financial education"
)


def create_stt() -> deepgram.STT | openai.STT | FasterWhisperSTT | None:
    if settings.stt_provider == "faster-whisper":
        logger.info("using faster-whisper STT (local, free)")
        return FasterWhisperSTT()

    if settings.stt_provider == "deepgram":
        api_key = settings.deepgram_api_key
        if api_key:
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
        logger.warning("DEEPGRAM_API_KEY not set — trying Groq Whisper fallback")

    if settings.groq_api_key:
        logger.info("using Groq Whisper STT (free tier)")
        return openai.STT(
            model="whisper-large-v3-turbo",
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
        )

    logger.error("no STT available — set DEEPGRAM_API_KEY or GROQ_API_KEY")
    return None


def create_llm() -> openai.LLM:
    if settings.llm_provider == "ollama":
        if not settings.ollama_base_url:
            logger.warning("OLLAMA_BASE_URL not set — LLM will fail at runtime")
        return openai.LLM(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            api_key="ollama",
        )

    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            logger.warning("GROQ_API_KEY not set — LLM will fail at runtime")
        return openai.LLM(
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
        )

    api_key = settings.openai_api_key
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — LLM will fail at runtime")
    return openai.LLM(
        model=settings.openai_model,
        api_key=api_key,
    )


async def _build_instructions(participant: str) -> str:
    instructions = _BASE_INSTRUCTIONS

    try:
        mem = await get_user_memory(participant)
        if mem:
            profile_parts = ["\n\nUser Profile:\n"]
            if mem.get("risk_profile"):
                profile_parts.append(f"- Risk Profile: {mem['risk_profile']}")
            if mem.get("goals"):
                profile_parts.append(f"- Goals: {', '.join(mem['goals'][:3])}")
            if mem.get("mentioned_products"):
                products = ", ".join(mem["mentioned_products"][:5])
                profile_parts.append(f"- Mentioned Products: {products}")
            if mem.get("bio"):
                profile_parts.append(f"- About the user: {mem['bio']}")
            profile_parts.append(f"- Conversation Count: {mem.get('conversation_count', 0)}")
            instructions += "\n".join(profile_parts)
    except Exception:
        logger.debug("could not load user memory", participant=participant)

    try:
        conversations = await get_recent_conversations(participant, limit=5)
        if conversations:
            history_parts = ["\n\nRecent Conversation History:\n"]
            for i, c in enumerate(conversations, 1):
                query = c["user_query"][:200] if c["user_query"] else ""
                response = c["agent_response"][:200] if c["agent_response"] else ""
                history_parts.append(f"  [{i}] User: {query}")
                history_parts.append(f"      Advisor: {response}")
            instructions += "\n".join(history_parts)
    except Exception:
        logger.debug("could not load conversation history", participant=participant)

    return instructions


def create_tts(*, voice_id: str | None = None) -> EdgeTTS | cartesia.TTS:
    if settings.tts_provider == "edge-tts":
        logger.info(
            "using EdgeTTS (free, no API key needed). "
            "Requires ffmpeg to be installed — see logs for installation instructions if not available."
        )
        return EdgeTTS(voice=voice_id) if voice_id else EdgeTTS()

    api_key = settings.cartesia_api_key
    if not api_key:
        logger.warning(
            "CARTESIA_API_KEY not set — falling back to EdgeTTS. "
            "Requires ffmpeg. Consider setting CARTESIA_API_KEY or TTS_PROVIDER=edge-tts"
        )
        return EdgeTTS()

    return cartesia.TTS(
        model="sonic-3",
        voice=voice_id or settings.cartesia_voice_id,
        speed=1.0,
        api_key=api_key,
    )


def create_session(
    *,
    vad_model: Any | None = None,
    voice_id: str | None = None,
) -> AgentSession[Any]:
    tts = create_tts(voice_id=voice_id)
    stt = create_stt()

    kwargs: dict[str, Any] = {}

    if tts is not None:
        kwargs["tts"] = tts
    else:
        logger.error("no TTS available — agent will speak using text only")

    if stt is not None:
        kwargs["stt"] = stt

    if vad_model is not None:
        kwargs["vad"] = vad_model

    llm = create_llm()
    kwargs["llm"] = llm

    return AgentSession(**kwargs)


async def create_agent(participant: str | None = None) -> Agent:
    instructions = await _build_instructions(participant) if participant else _BASE_INSTRUCTIONS

    return Agent(
        instructions=instructions,
        tools=FINANCE_TOOLS,  # type: ignore[arg-type]
    )


async def run_agent(ctx: JobContext) -> None:
    participant = await ctx.wait_for_participant()
    user_id = participant.identity

    logger.info(
        "agent session started",
        room=ctx.room.name,
        participant=user_id,
    )

    vad = ctx.proc.userdata.get("vad")
    session = create_session(vad_model=vad)
    agent = await create_agent(participant=user_id)

    close_event = asyncio.Event()
    last_user_query: str | None = None

    @session.on("conversation_item_added")
    def on_conversation_item(item: Any) -> None:
        nonlocal last_user_query
        try:
            if not hasattr(item, "role") or not hasattr(item, "text"):
                return
            text = str(item.text)[:1000] if item.text else ""
            if item.role == "user":
                last_user_query = text
            elif item.role == "assistant" and last_user_query:
                asyncio.ensure_future(
                    record_interaction(
                        room=ctx.room.name,
                        participant=user_id,
                        user_query=last_user_query,
                        agent_response=text,
                    )
                )
                last_user_query = None
        except Exception:
            logger.exception("failed to log conversation item")

    @session.on("function_tools_executed")
    def on_tools_executed(call_info: Any) -> None:
        try:
            tools = []
            if hasattr(call_info, "tools"):
                tools = [t.name for t in call_info.tools if hasattr(t, "name")]
            if tools:
                asyncio.ensure_future(
                    upsert_user_memory(
                        user_id=user_id,
                        topics=tools,
                    )
                )
        except Exception:
            logger.exception("failed to log tool execution")

    @session.on("close")
    def on_close() -> None:
        close_event.set()

    await session.start(agent=agent, room=ctx.room)

    async def _visual_monitor() -> None:
        last_alert: str | None = None
        while not close_event.is_set():
            await asyncio.sleep(5)
            try:
                meta = visual_state_store.get(user_id)
                if meta is None or not meta.face_detected:
                    visual_state_store.store_note(user_id, None)
                    visual_state_store.store_note("latest", None)
                    continue
                alert: str | None = None
                if meta.looking_away_sec > 5:
                    alert = f"User looking away for {meta.looking_away_sec:.0f}s (engagement {meta.engagement:.2f})"
                elif meta.engagement < 0.3:
                    alert = f"Low user engagement ({meta.engagement:.2f}) — user may be distracted"
                if alert and alert != last_alert:
                    logger.info("visual context: %s", alert)
                    visual_state_store.store_note(user_id, alert)
                    visual_state_store.store_note("latest", alert)
                    last_alert = alert
                elif not alert:
                    visual_state_store.store_note(user_id, None)
                    visual_state_store.store_note("latest", None)
                    last_alert = None
            except Exception:
                logger.exception("visual monitor error")

    monitor_task = asyncio.create_task(_visual_monitor())
    await close_event.wait()
    monitor_task.cancel()

    logger.info(
        "agent session ended",
        room=ctx.room.name,
        participant=user_id,
    )

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    model: str
    provider: str
    latency_ms: int


@router.post("/chat")
async def debug_chat(req: ChatRequest) -> ChatResponse:
    logger.info("=== DEBUG CHAT ===")
    logger.info("input message=%s", req.message[:200])

    t0 = time.perf_counter()

    try:
        from livekit.plugins import openai as lk_openai

        if settings.llm_provider == "groq":
            logger.info("creating Groq LLM")
            llm = lk_openai.LLM(
                model=settings.groq_model,
                base_url=settings.groq_base_url,
                api_key=settings.groq_api_key,
            )
        elif settings.llm_provider == "ollama":
            logger.info("creating Ollama LLM")
            llm = lk_openai.LLM(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                api_key="ollama",
            )
        else:
            logger.info("creating OpenAI LLM")
            llm = lk_openai.LLM(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
            )

        logger.info("LLM model=%s provider=%s", llm.model, llm.provider)

        from livekit.agents.llm import ChatContext, ChatMessage

        ctx = ChatContext(
            items=[
                ChatMessage(
                    role="system",
                    content=[
                        "You are a knowledgeable personal finance advisor for Indian users. "
                        "Provide clear, accurate, and responsible financial guidance.\n\n"
                        "Guidelines:\n"
                        "- Never give stock tips, guaranteed returns, or specific stock recommendations.\n"
                        "- Always include a disclaimer about consulting a SEBI-registered advisor.\n"
                        "- Be friendly, patient, and educational."
                    ],
                ),
                ChatMessage(role="user", content=[req.message]),
            ]
        )

        logger.info("sending request to LLM")
        stream = llm.chat(chat_ctx=ctx)

        full_text = ""
        async for text in stream.to_str_iterable():
            full_text += text

        if not full_text:
            full_text = "(no response from LLM)"

        latency = int((time.perf_counter() - t0) * 1000)
        logger.info("LLM response received in %dms", latency)
        logger.info("response=%s", full_text[:300])

        return ChatResponse(
            response=full_text,
            model=llm.model,
            provider=llm.provider,
            latency_ms=latency,
        )

    except Exception as e:
        logger.exception("debug chat failed")
        raise HTTPException(status_code=500, detail=str(e))

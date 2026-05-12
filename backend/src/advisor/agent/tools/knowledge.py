from __future__ import annotations

import asyncio

from livekit.agents.llm import function_tool

from ...core.logging import get_logger
from ...rag.retriever import FinanceRetriever

logger = get_logger(__name__)

_retriever: FinanceRetriever | None = None


def get_retriever() -> FinanceRetriever:
    global _retriever
    if _retriever is None:
        _retriever = FinanceRetriever()
    return _retriever


@function_tool
async def lookup_finance_knowledge(query: str) -> str:
    """Search the financial knowledge base for relevant information about
    Indian financial products, tax rules, investment options, regulations,
    and personal finance concepts. Use this whenever the user asks about
    specific financial topics, products, or rules."""
    try:
        retriever = get_retriever()
        context = await asyncio.to_thread(retriever.retrieve_formatted, query)
        if not context:
            return "No relevant information found in the knowledge base."
        return context
    except Exception:
        logger.exception("knowledge lookup failed", query=query[:80])
        return "I encountered an error while searching my knowledge base. Please try again."

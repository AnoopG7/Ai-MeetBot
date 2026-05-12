from __future__ import annotations

import asyncio

from livekit.agents import AgentServer, JobContext

from ..core.logging import configure_logging, get_logger
from .prewarm import prewarm
from .session import run_agent

logger = get_logger(__name__)

server = AgentServer()
server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    """Entrypoint for LiveKit job assignment.

    Phase 3: Full speech pipeline — VAD + STT + LLM + TTS.
    """
    try:
        await run_agent(ctx)
    except asyncio.CancelledError:
        logger.info("agent session cancelled")
        raise
    except Exception:
        logger.exception("agent session failed")
        raise


def run() -> None:
    configure_logging()
    logger.info("starting agent server")
    asyncio.run(server.run())


if __name__ == "__main__":
    run()

from __future__ import annotations

import asyncio

from livekit.agents import AgentServer, JobContext

from ..core.logging import configure_logging, get_logger

logger = get_logger(__name__)

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    """Called when a job is assigned (user connects to the LiveKit room).

    Phase 1: connects, logs, stays alive until room closes.
    Phase 5+: full conversational loop with AgentSession.
    """
    participant = await ctx.wait_for_participant()
    logger.info(
        "agent session started",
        room=ctx.room.name,
        participant=participant.identity,
    )

    # Block until cancelled by the framework when the job ends
    await asyncio.Event().wait()


def run() -> None:
    configure_logging()
    logger.info("starting agent server")
    asyncio.run(server.run())


if __name__ == "__main__":
    run()

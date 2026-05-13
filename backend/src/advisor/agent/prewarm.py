from __future__ import annotations

from livekit.agents import JobProcess
from livekit.plugins import silero

from ..core.logging import get_logger

logger = get_logger(__name__)


def prewarm(proc: JobProcess) -> None:
    """Preload the Silero VAD model during process initialization.

    Called once per child process before any job runs in that process.
    The loaded model is stored in proc.userdata for reuse across jobs.
    """
    logger.info("prewarming Silero VAD model")
    vad = silero.VAD.load(
        min_speech_duration=0.05,
        min_silence_duration=1.2,
        prefix_padding_duration=0.5,
        activation_threshold=0.5,
    )
    proc.userdata["vad"] = vad
    logger.info("Silero VAD model loaded")

from __future__ import annotations

import asyncio
import shutil
import subprocess

import edge_tts
from livekit.agents import tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
from livekit.agents.utils import shortuuid

from ..core.logging import get_logger

SAMPLE_RATE = 24000
NUM_CHANNELS = 1

DEFAULT_VOICE = "en-US-JennyNeural"
TTS_TIMEOUT = 20.0

logger = get_logger(__name__)

# Check if ffmpeg is available at startup
_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
if not _FFMPEG_AVAILABLE:
    logger.warning(
        "ffmpeg not found in system PATH — TTS will fail at runtime. "
        "Install ffmpeg: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
    )


class EdgeTTS(tts.TTS):
    def __init__(self, voice: str = DEFAULT_VOICE) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )
        self._voice = voice

    @property
    def model(self) -> str:
        return "edge-tts"

    @property
    def provider(self) -> str:
        return "edge-tts (microsoft)"

    def synthesize(
        self,
        text: str,
        *,
        conn_options: tts.APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> tts.ChunkedStream:
        return EdgeTTSChunkedStream(tts=self, input_text=text, conn_options=conn_options)


class EdgeTTSChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts: EdgeTTS,
        input_text: str,
        conn_options: tts.APIConnectOptions,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._edge_tts: EdgeTTS = tts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        text_preview = self.input_text[:60].replace("\n", " ")
        logger.info("synthesizing speech", text=text_preview)

        if not _FFMPEG_AVAILABLE:
            logger.error("ffmpeg not available — cannot synthesize audio")
            output_emitter.flush()
            return

        output_emitter.initialize(
            request_id=shortuuid(),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
            mime_type="audio/pcm",
        )

        communicate = edge_tts.Communicate(self.input_text, voice=self._edge_tts._voice)

        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i",
                "pipe:0",
                "-f",
                "s16le",
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                str(NUM_CHANNELS),
                "pipe:1",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as e:
            logger.error("failed to start ffmpeg subprocess", error=str(e))
            output_emitter.flush()
            return

        try:
            async with asyncio.timeout(TTS_TIMEOUT):
                chunk_count = 0
                try:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio" and proc.stdin:
                            proc.stdin.write(chunk["data"])
                            chunk_count += 1
                except Exception as e:
                    logger.error("edge-tts streaming error", error=str(e))
                    if proc.stdin:
                        proc.stdin.close()
                    proc.kill()
                    output_emitter.flush()
                    return

                logger.info("edge-tts streaming complete", chunks=chunk_count)

                if proc.stdin:
                    await proc.stdin.drain()
                    proc.stdin.close()

                # Read output from ffmpeg
                total = 0
                try:
                    while True:
                        chunk = await proc.stdout.read(8192)
                        if not chunk:
                            break
                        output_emitter.push(chunk)
                        total += len(chunk)
                except Exception as e:
                    logger.error("error reading ffmpeg output", error=str(e))

                await proc.wait()
                
                if total == 0:
                    logger.warning("tts synthesis produced no audio output", text=text_preview)
                else:
                    logger.info("tts synthesis complete", pcm_bytes=total)
        except asyncio.TimeoutError:
            logger.error("tts synthesis timed out", seconds=TTS_TIMEOUT, text=text_preview)
            if proc.stdin:
                proc.stdin.close()
            proc.kill()
        except Exception as e:
            logger.exception("tts synthesis failed", text=text_preview, error=str(e))
            if proc.stdin:
                proc.stdin.close()
            proc.kill()
        finally:
            output_emitter.flush()

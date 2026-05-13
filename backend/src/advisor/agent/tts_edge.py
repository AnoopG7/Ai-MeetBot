from __future__ import annotations

import asyncio
import subprocess

import edge_tts
from livekit.agents import tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
from livekit.agents.utils import shortuuid

SAMPLE_RATE = 24000
NUM_CHANNELS = 1

DEFAULT_VOICE = "en-US-JennyNeural"


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
        output_emitter.initialize(
            request_id=shortuuid(),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
            mime_type="audio/pcm",
        )

        communicate = edge_tts.Communicate(self.input_text, voice=self._edge_tts._voice)

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
            stderr=subprocess.DEVNULL,
        )

        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and proc.stdin:
                proc.stdin.write(chunk["data"])

        if proc.stdin:
            proc.stdin.close()

        while True:
            chunk = await proc.stdout.read(8192)
            if not chunk:
                break
            output_emitter.push(chunk)

        await proc.wait()
        output_emitter.flush()

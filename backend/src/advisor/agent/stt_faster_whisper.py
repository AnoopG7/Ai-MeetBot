from __future__ import annotations

import asyncio
import logging

import numpy as np
from faster_whisper import WhisperModel

from livekit import rtc
from livekit.agents import stt as stt_module
from livekit.agents.stt import (
    STT,
    STTCapabilities,
    SpeechData,
    SpeechEvent,
    SpeechEventType,
)
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)
from livekit.agents.utils import AudioBuffer, is_given

from ..core.logging import get_logger

logger = get_logger(__name__)

SAMPLE_RATE = 16000


class FasterWhisperSTT(STT):
    def __init__(
        self,
        *,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        super().__init__(
            capabilities=STTCapabilities(
                streaming=False,
                interim_results=False,
                offline_recognize=True,
            ),
        )
        self._model_size = model_size
        logger.info(
            "loading faster-whisper model",
            model=model_size,
            device=device,
            compute_type=compute_type,
        )
        self._model = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )
        logger.info("faster-whisper model loaded")

    @property
    def model(self) -> str:
        return f"faster-whisper-{self._model_size}"

    @property
    def provider(self) -> str:
        return "faster-whisper"

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> SpeechEvent:
        if isinstance(buffer, rtc.AudioFrame):
            frames = [buffer]
        else:
            frames = list(buffer)

        if not frames:
            return SpeechEvent(
                type=SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[SpeechData(language="en", text="")],
            )

        src_sr = frames[0].sample_rate
        pcm_data = b"".join(bytes(f.data) for f in frames)

        samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0

        if src_sr != SAMPLE_RATE:
            samples = _resample(samples, src_sr, SAMPLE_RATE)

        loop = asyncio.get_event_loop()
        lang: str | None = language if is_given(language) else None

        def _transcribe() -> list[tuple[str, str | None]]:
            segs, _ = self._model.transcribe(
                samples,
                beam_size=5,
                language=lang or "en",
                vad_filter=True,
            )
            return [(s.text, s.language if hasattr(s, "language") else None) for s in segs]

        segments = await loop.run_in_executor(None, _transcribe)

        text = " ".join(s[0] for s in segments if s[0]).strip()

        return SpeechEvent(
            type=SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[
                SpeechData(
                    language="en",
                    text=text,
                )
            ],
        )


def _resample(data: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    src_len = len(data)
    dst_len = int(src_len * dst_rate / src_rate)
    indices = np.linspace(0, src_len - 1, dst_len)
    return np.interp(indices, np.arange(src_len), data).astype(np.float32)

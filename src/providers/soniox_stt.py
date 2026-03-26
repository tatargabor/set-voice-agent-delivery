"""Soniox streaming STT provider using AsyncRealtimeSTTSession."""

import asyncio
import time
from typing import AsyncIterator

import structlog
from soniox import AsyncSonioxClient
from soniox.types import RealtimeSTTConfig

from .base import STTProvider, TranscriptEvent

log = structlog.get_logger()


class SonioxSTTProvider(STTProvider):
    """Speech-to-Text via Soniox real-time WebSocket API."""

    def __init__(
        self,
        model: str = "stt-rt-v4",
        sample_rate: int = 8000,
        endpoint_delay_ms: int | None = None,
    ):
        from ..config import get_settings
        settings = get_settings()
        self._model = model
        self._sample_rate = sample_rate
        self._endpoint_delay_ms = endpoint_delay_ms or settings.voice.endpoint_delay_ms
        self._interim_enabled = settings.voice.interim_enabled
        self._interim_min_words = settings.voice.interim_min_words
        self._interim_silence_ms = settings.voice.interim_silence_ms
        self._client: AsyncSonioxClient | None = None
        self._session = None

    async def connect(self) -> None:
        """Establish WebSocket connection to Soniox."""
        self._client = AsyncSonioxClient()
        config = RealtimeSTTConfig(
            model=self._model,
            audio_format="mulaw",
            sample_rate=self._sample_rate,
            num_channels=1,
            language_hints=["hu"],
            language_hints_strict=True,
            enable_endpoint_detection=True,
            max_endpoint_delay_ms=self._endpoint_delay_ms,
        )
        self._session = await self._client.realtime.stt.connect(config=config).__aenter__()

    async def disconnect(self) -> None:
        """Close the WebSocket session."""
        if self._session is not None:
            await self._session.__aexit__(None, None, None)
            self._session = None
        self._client = None

    async def transcribe_stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[TranscriptEvent]:
        """Send audio chunks to Soniox, yield TranscriptEvent objects.

        When interim is enabled, yields speculative interim events when enough
        words accumulate and silence is detected. Always yields a final event
        on endpoint detection (<fin>/<end>).
        """
        if self._session is None:
            raise RuntimeError("Not connected. Call connect() first.")

        # Start a task to feed audio
        async def _feed_audio():
            async for chunk in audio_chunks:
                await self._session.send_byte_chunk(chunk)
            await self._session.finalize()

        feed_task = asyncio.create_task(_feed_audio())

        try:
            if self._interim_enabled:
                async for event in self._transcribe_with_interim():
                    yield event
            else:
                async for event in self._transcribe_final_only():
                    yield event
        finally:
            feed_task.cancel()
            try:
                await feed_task
            except asyncio.CancelledError:
                pass

    async def _transcribe_final_only(self) -> AsyncIterator[TranscriptEvent]:
        """Original logic — only yield on <fin>/<end>."""
        current_text = ""
        async for event in self._session.receive_events():
            for token in event.tokens:
                if token.text in ("<fin>", "<end>"):
                    if current_text.strip():
                        yield TranscriptEvent(text=current_text.strip(), is_interim=False)
                        current_text = ""
                elif getattr(token, "is_final", True):
                    current_text += token.text

    async def _transcribe_with_interim(self) -> AsyncIterator[TranscriptEvent]:
        """Interim-aware logic — yield speculative events on silence gaps.

        Uses a queue bridge to avoid cancelling __anext__() on the Soniox
        async iterator, which can corrupt its internal state.
        """
        current_text = ""
        interim_yielded = False
        silence_timeout = self._interim_silence_ms / 1000.0

        # Bridge: read Soniox events into a queue so we can poll with timeout
        _SENTINEL = object()
        event_queue: asyncio.Queue = asyncio.Queue()

        async def _reader():
            try:
                async for event in self._session.receive_events():
                    await event_queue.put(event)
            finally:
                await event_queue.put(_SENTINEL)

        reader_task = asyncio.create_task(_reader())

        try:
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=silence_timeout)
                except asyncio.TimeoutError:
                    # Silence gap detected — check if we should yield interim
                    if not interim_yielded and current_text.strip():
                        word_count = len(current_text.strip().split())
                        if word_count >= self._interim_min_words:
                            log.info("interim_transcript", text=current_text.strip(), words=word_count)
                            yield TranscriptEvent(text=current_text.strip(), is_interim=True)
                            interim_yielded = True
                    continue

                if event is _SENTINEL:
                    # Stream ended — yield any remaining text as final
                    if current_text.strip():
                        yield TranscriptEvent(text=current_text.strip(), is_interim=False)
                    break

                for token in event.tokens:
                    if token.text in ("<fin>", "<end>"):
                        if current_text.strip():
                            yield TranscriptEvent(text=current_text.strip(), is_interim=False)
                            current_text = ""
                            interim_yielded = False
                    elif getattr(token, "is_final", True):
                        current_text += token.text
        finally:
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass

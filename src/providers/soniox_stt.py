"""Soniox streaming STT provider using AsyncRealtimeSTTSession."""

import asyncio
from typing import AsyncIterator

from soniox import AsyncSonioxClient
from soniox.types import RealtimeSTTConfig

from .base import STTProvider


class SonioxSTTProvider(STTProvider):
    """Speech-to-Text via Soniox real-time WebSocket API."""

    def __init__(
        self,
        model: str = "stt-rt-v4",
        sample_rate: int = 8000,
        endpoint_delay_ms: int = 800,
    ):
        self._model = model
        self._sample_rate = sample_rate
        self._endpoint_delay_ms = endpoint_delay_ms
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

    async def transcribe_stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Send audio chunks to Soniox, yield transcript strings.

        Yields partial transcript strings as tokens arrive. Finalized
        transcripts (after endpoint detection) are yielded as complete strings.
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
            current_text = ""
            async for event in self._session.receive_events():
                for token in event.tokens:
                    if token.text in ("<fin>", "<end>"):
                        if current_text.strip():
                            yield current_text.strip()
                            current_text = ""
                    elif getattr(token, "is_final", True):
                        # Only accumulate finalized tokens to avoid partial duplicates
                        current_text += token.text
        finally:
            feed_task.cancel()
            try:
                await feed_task
            except asyncio.CancelledError:
                pass

"""Abstract base classes for voice agent providers."""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class STTProvider(ABC):
    """Speech-to-Text provider interface."""

    @abstractmethod
    async def transcribe_stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Stream audio chunks, yield partial transcripts."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to STT service."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""


class TTSProvider(ABC):
    """Text-to-Speech provider interface."""

    @abstractmethod
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Convert text to audio, yield audio chunks."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to TTS service."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""


class TelephonyProvider(ABC):
    """Telephony provider interface."""

    @abstractmethod
    async def place_call(self, phone_number: str, webhook_url: str) -> str:
        """Place an outbound call. Returns call SID/ID."""

    @abstractmethod
    async def hangup(self, call_id: str) -> None:
        """Hang up an active call."""

    @abstractmethod
    async def get_audio_stream(self, call_id: str) -> AsyncIterator[bytes]:
        """Get incoming audio stream from active call."""

    @abstractmethod
    async def send_audio(self, call_id: str, audio: bytes) -> None:
        """Send audio to active call."""

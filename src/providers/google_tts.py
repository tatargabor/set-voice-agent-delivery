"""Google Cloud Text-to-Speech provider."""

from typing import AsyncIterator

from google.cloud import texttospeech

from .base import TTSProvider

# Chunk size for streaming audio output (4KB)
_CHUNK_SIZE = 4096


class GoogleTTSProvider(TTSProvider):
    """Text-to-Speech via Google Cloud TTS API.

    Outputs mulaw 8kHz mono audio to match Twilio Media Streams format.
    """

    def __init__(
        self,
        language_code: str = "hu-HU",
        voice_name: str | None = None,
        sample_rate: int = 8000,
    ):
        self._language_code = language_code
        self._voice_name = voice_name
        self._sample_rate = sample_rate
        self._client: texttospeech.TextToSpeechClient | None = None

    async def connect(self) -> None:
        """Initialize the Google Cloud TTS client."""
        self._client = texttospeech.TextToSpeechClient()

    async def disconnect(self) -> None:
        """Release client resources."""
        if self._client is not None:
            self._client.transport.close()
            self._client = None

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Synthesize text to mulaw 8kHz audio, yield chunks.

        Note: Google Cloud TTS returns the full audio in one response.
        We chunk it to allow streaming playback.
        """
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        input_text = texttospeech.SynthesisInput(text=text)

        voice_params = texttospeech.VoiceSelectionParams(
            language_code=self._language_code,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
        )
        if self._voice_name:
            voice_params.name = self._voice_name

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MULAW,
            sample_rate_hertz=self._sample_rate,
        )

        response = self._client.synthesize_speech(
            input=input_text, voice=voice_params, audio_config=audio_config
        )

        audio = response.audio_content
        # Strip WAV header (44 bytes) — raw mulaw data only, avoids clicks between chunks
        if audio[:4] == b'RIFF':
            audio = audio[44:]
        for i in range(0, len(audio), _CHUNK_SIZE):
            yield audio[i : i + _CHUNK_SIZE]

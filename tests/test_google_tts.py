"""Integration test for Google Cloud TTS provider (requires GOOGLE_APPLICATION_CREDENTIALS)."""

import pytest
from src.providers.google_tts import GoogleTTSProvider


@pytest.mark.audio_loop
async def test_tts_synthesizes_hungarian():
    """Google TTS should produce mulaw audio from Hungarian text."""
    tts = GoogleTTSProvider()
    await tts.connect()

    audio_bytes = b""
    async for chunk in tts.synthesize_stream("Szia, ez egy teszt."):
        audio_bytes += chunk

    await tts.disconnect()

    assert len(audio_bytes) > 1000, f"Expected substantial audio, got {len(audio_bytes)} bytes"
    # mulaw audio doesn't have a magic header, but we can check it's non-silence
    assert not all(b == 0xFF for b in audio_bytes[:100]), "Audio should not be silence"

"""Integration test for Soniox STT provider (requires SONIOX_API_KEY)."""

import pytest
from src.providers.soniox_stt import SonioxSTTProvider
from src.providers.google_tts import GoogleTTSProvider


@pytest.mark.audio_loop
async def test_stt_transcribes_hungarian_audio():
    """Generate Hungarian audio via Google TTS, then transcribe it via Soniox STT."""
    # First, generate a known Hungarian audio sample
    tts = GoogleTTSProvider()
    await tts.connect()
    audio_bytes = b""
    async for chunk in tts.synthesize_stream("Helló, ez egy teszt mondat."):
        audio_bytes += chunk
    await tts.disconnect()

    assert len(audio_bytes) > 0, "TTS should produce audio"

    # Now transcribe it
    stt = SonioxSTTProvider()
    await stt.connect()

    async def _audio_source():
        # Send in small chunks like a real stream
        chunk_size = 640  # 40ms at 8kHz mulaw
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i : i + chunk_size]

    transcripts = []
    async for event in stt.transcribe_stream(_audio_source()):
        transcripts.append(event.text)

    await stt.disconnect()

    full_text = " ".join(transcripts).lower()
    assert len(full_text) > 0, "Should produce some transcript"
    # Check that at least part of the expected text appears
    assert any(word in full_text for word in ["helló", "hello", "teszt", "mondat"]), (
        f"Transcript should contain Hungarian words, got: {full_text}"
    )

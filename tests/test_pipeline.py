"""Level 1 integration test: audio round-trip through the pipeline.

Requires: SONIOX_API_KEY, GOOGLE_APPLICATION_CREDENTIALS, ANTHROPIC_API_KEY
"""

import asyncio
import pytest
from src.agent import ConversationAgent, CallContext
from src.providers.soniox_stt import SonioxSTTProvider
from src.providers.google_tts import GoogleTTSProvider
from src.state import CallState


@pytest.fixture
def call_context():
    return CallContext(
        customer_name="Teszt Elek",
        company_name="WebBuilder Kft.",
        purpose="Megkérdezni megkapta-e a levelet a weboldaláról",
        website_url="https://teszt-elek.hu",
    )


@pytest.mark.audio_loop
async def test_tts_to_stt_roundtrip():
    """Generate Hungarian audio via TTS, transcribe via STT, verify text."""
    tts = GoogleTTSProvider()
    stt = SonioxSTTProvider()

    await tts.connect()
    await stt.connect()

    try:
        # Generate audio from known text
        source_text = "Igen, megkaptam a levelet, köszönöm."
        audio_bytes = b""
        async for chunk in tts.synthesize_stream(source_text):
            audio_bytes += chunk

        assert len(audio_bytes) > 0

        # Transcribe the audio
        async def _audio_source():
            chunk_size = 640
            for i in range(0, len(audio_bytes), chunk_size):
                yield audio_bytes[i : i + chunk_size]

        transcripts = []
        async for text in stt.transcribe_stream(_audio_source()):
            transcripts.append(text)

        full_text = " ".join(transcripts).lower()
        assert len(full_text) > 0, "Should produce transcript"
        assert any(w in full_text for w in ["igen", "megkaptam", "levelet", "köszönöm"]), (
            f"Expected Hungarian words in transcript, got: {full_text}"
        )
    finally:
        await stt.disconnect()
        await tts.disconnect()


@pytest.mark.audio_loop
async def test_agent_response_to_audio(call_context):
    """TTS → STT → Claude → verify agent responds meaningfully."""
    tts = GoogleTTSProvider()
    stt = SonioxSTTProvider()
    agent = ConversationAgent()

    await tts.connect()
    await stt.connect()

    try:
        # Simulate customer saying something
        customer_audio = b""
        async for chunk in tts.synthesize_stream("Igen, megkaptam a levelet."):
            customer_audio += chunk

        # Transcribe
        async def _audio_source():
            chunk_size = 640
            for i in range(0, len(customer_audio), chunk_size):
                yield customer_audio[i : i + chunk_size]

        transcripts = []
        async for text in stt.transcribe_stream(_audio_source()):
            transcripts.append(text)

        customer_text = " ".join(transcripts)
        assert len(customer_text) > 0, "STT should produce text"

        # Get agent greeting first, then respond to customer
        await agent.get_greeting(call_context)
        response, _ = await agent.respond(call_context, customer_text)
        assert len(response) > 5, f"Agent should give meaningful response, got: {response}"

        # Synthesize agent response back to audio
        response_audio = b""
        async for chunk in tts.synthesize_stream(response):
            response_audio += chunk

        assert len(response_audio) > 0, "TTS should produce audio from agent response"
    finally:
        await stt.disconnect()
        await tts.disconnect()

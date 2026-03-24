## Context

The project has abstract provider interfaces (`STTProvider`, `TTSProvider`, `TelephonyProvider` in `src/providers/base.py`) but no concrete implementations. The `ConversationAgent` in `src/agent.py` works with text only. We need real providers to connect speech and telephony.

Key discovery: **Soniox only provides STT, not TTS.** We need a separate TTS solution.

Current state:
- Soniox Python SDK (`soniox` 2.2.0) — async WebSocket STT with Hungarian support, endpoint detection (VAD)
- Twilio — REST API for call placement, Media Streams WebSocket for bidirectional audio
- No TTS in Soniox SDK

## Goals / Non-Goals

**Goals:**
- Implement concrete STT provider using Soniox real-time WebSocket API
- Implement concrete TTS provider (provider TBD — see Decisions)
- Implement concrete Telephony provider using Twilio
- Load credentials from `.env` at startup with validation
- Each provider independently testable

**Non-Goals:**
- Call pipeline orchestration (Change 2)
- Turn management, barge-in, state machine (Change 2)
- Webhook server, DNC checks, call script loading (Change 3)
- Multi-language support (Hungarian only for now)

## Decisions

### 1. STT: Soniox AsyncRealtimeSTTSession

Use `soniox` SDK's async WebSocket client directly.

```
Audio flow: Twilio mulaw 8kHz → session.send_byte_chunk() → event.tokens
```

Config:
- Model: `stt-rt-v4`
- Audio format: `mulaw`, 8kHz, mono (matches Twilio Media Streams)
- Language: `hu` with `language_hints_strict=True`
- Endpoint detection: enabled, `max_endpoint_delay_ms=1500`

**Why Soniox over alternatives:** Already chosen by project, good Hungarian support, built-in VAD/endpoint detection, async WebSocket streaming.

### 2. TTS: Google Cloud Text-to-Speech

Soniox has no TTS. Options considered:

| Provider | Hungarian | Streaming | Latency | Cost |
|----------|-----------|-----------|---------|------|
| Google Cloud TTS | hu-HU, multiple voices | Yes (gRPC) | Low | $4/1M chars |
| ElevenLabs | Limited Hungarian | Yes | Medium | $5/100K chars |
| Azure TTS | hu-HU, neural voices | Yes (WebSocket) | Low | $4/1M chars |

**Decision: Google Cloud TTS** — best Hungarian voice quality with neural voices, streaming support via gRPC, reasonable cost. Output as mulaw 8kHz to match Twilio directly.

Alternative considered: Azure TTS has similar quality but adds Azure dependency alongside GCP. ElevenLabs is too expensive for production volume and Hungarian support is limited.

**Dependency:** `google-cloud-texttospeech` package. Requires `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_CLOUD_API_KEY`.

### 3. Twilio: Media Streams WebSocket

Twilio Media Streams sends/receives audio over WebSocket:
- Inbound: base64-encoded mulaw 8kHz chunks in JSON messages
- Outbound: same format, send `media` messages back

This means the TelephonyProvider needs a WebSocket server that Twilio connects TO (not a client connecting out). This will be a simple WebSocket handler; the full webhook HTTP server comes in Change 3.

### 4. Config: python-dotenv with validation

`src/config.py` loads `.env` and validates required keys per provider:
- Always: `ANTHROPIC_API_KEY`
- If STT: `SONIOX_API_KEY`
- If TTS: `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_CLOUD_API_KEY`
- If telephony: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`

Fail fast with clear error messages listing missing keys.

### 5. File structure

```
src/
├── config.py                    # .env loading + validation
├── providers/
│   ├── base.py                  # existing ABCs (unchanged)
│   ├── soniox_stt.py           # SonioxSTTProvider
│   ├── google_tts.py           # GoogleTTSProvider
│   └── twilio_provider.py      # TwilioTelephonyProvider
```

## Risks / Trade-offs

- **[Risk] Google Cloud TTS adds a new cloud dependency** → Mitigation: Isolated behind TTSProvider ABC, swappable later. Could also use a simpler HTTP-based TTS as fallback.
- **[Risk] Twilio Media Streams requires WebSocket server** → Mitigation: Keep it minimal in this change, full HTTP server in Change 3.
- **[Risk] Soniox SDK version changes** → Mitigation: Pin `soniox>=2.2.0,<3.0` in pyproject.toml.
- **[Trade-off] mulaw 8kHz throughout** → Lower quality than 16kHz PCM, but avoids transcoding between Twilio and providers. Acceptable for phone calls.

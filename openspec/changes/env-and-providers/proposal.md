## Why

The project has abstract provider interfaces (STT, TTS, Telephony) but no concrete implementations. Without real providers, the voice agent cannot process speech or place calls. This change adds the foundational provider layer — Soniox for speech and Twilio for telephony — plus environment variable loading so credentials are managed safely.

## What Changes

- Add `python-dotenv` dependency and `.env` loading at startup
- Implement `SonioxSTTProvider` — streaming speech-to-text over WebSocket, Hungarian (hu-HU)
- Implement `SonioxTTSProvider` — streaming text-to-speech, Hungarian voice
- Implement `TwilioTelephonyProvider` — outbound call placement, audio stream access via Media Streams
- Add unit/integration tests for each provider

## Capabilities

### New Capabilities
- `env-loading`: Load configuration from `.env` files using python-dotenv, validate required keys at startup
- `soniox-stt`: Streaming speech-to-text via Soniox WebSocket API with Hungarian language support
- `soniox-tts`: Streaming text-to-speech via Soniox API with Hungarian voice
- `twilio-telephony`: Outbound call placement and bidirectional audio streaming via Twilio Media Streams

### Modified Capabilities
<!-- None — no existing specs to modify -->

## Impact

- **Dependencies**: adds `python-dotenv` to pyproject.toml
- **Code**: new files under `src/providers/` (soniox_stt.py, soniox_tts.py, twilio_provider.py) and `src/config.py`
- **APIs**: depends on Soniox API (WebSocket), Twilio REST API + Media Streams WebSocket
- **Environment**: requires SONIOX_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, ANTHROPIC_API_KEY

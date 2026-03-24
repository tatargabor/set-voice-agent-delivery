## 1. Environment Loading

- [x] 1.1 Add `python-dotenv` to pyproject.toml dependencies
- [x] 1.2 Create `src/config.py` — load `.env`, validate required keys per provider, return typed config object
- [x] 1.3 Add test for config validation (missing keys → clear error, present keys → config object)

## 2. Soniox STT Provider

- [x] 2.1 Add `soniox>=2.2.0,<3.0` to pyproject.toml dependencies
- [x] 2.2 Create `src/providers/soniox_stt.py` — `SonioxSTTProvider(STTProvider)` using `AsyncRealtimeSTTSession`
- [x] 2.3 Configure: model `stt-rt-v4`, mulaw 8kHz mono, `language_hints=["hu"]`, `language_hints_strict=True`, endpoint detection 1500ms
- [x] 2.4 Implement `connect()` / `disconnect()` for WebSocket lifecycle
- [x] 2.5 Implement `transcribe_stream()` — send audio chunks, yield transcript strings from token events
- [x] 2.6 Add integration test: stream a Hungarian audio sample → verify transcript output (requires SONIOX_API_KEY)

## 3. Google Cloud TTS Provider

- [x] 3.1 Add `google-cloud-texttospeech` to pyproject.toml dependencies
- [x] 3.2 Create `src/providers/google_tts.py` — `GoogleTTSProvider(TTSProvider)`
- [x] 3.3 Configure: hu-HU neural voice, mulaw 8kHz mono output
- [x] 3.4 Implement `connect()` / `disconnect()` for client lifecycle
- [x] 3.5 Implement `synthesize_stream(text)` — send text, yield audio byte chunks
- [x] 3.6 Add integration test: synthesize Hungarian text → verify audio bytes returned (requires GOOGLE_APPLICATION_CREDENTIALS)

## 4. Twilio Telephony Provider

- [x] 4.1 Verify `twilio>=9.0` already in pyproject.toml
- [x] 4.2 Create `src/providers/twilio_provider.py` — `TwilioTelephonyProvider(TelephonyProvider)`
- [x] 4.3 Implement `place_call(phone_number, webhook_url)` — Twilio REST API, return Call SID
- [x] 4.4 Implement `hangup(call_id)` — terminate call via REST API
- [x] 4.5 Implement `get_audio_stream(call_id)` — decode base64 mulaw from Media Streams WebSocket messages, yield raw bytes
- [x] 4.6 Implement `send_audio(call_id, audio_bytes)` — encode to base64, send as Twilio media message
- [x] 4.7 Add integration test: place call + hangup (requires TWILIO credentials, uses verified number)

## 5. Wiring

- [x] 5.1 Update `src/providers/__init__.py` — export all concrete providers
- [x] 5.2 Update `.env.example` with all required keys (add GOOGLE_APPLICATION_CREDENTIALS)

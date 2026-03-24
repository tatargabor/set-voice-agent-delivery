# Voice AI Patterns

## Audio Streaming
- STT and TTS MUST use async streaming — never block the event loop
- Buffer audio in chunks before sending to reduce API calls
- Use Voice Activity Detection (VAD) to detect when the customer stops speaking
- Handle connection drops gracefully — reconnect and resume

## Claude Conversation
- Keep responses short: 1-2 sentences max — this is a phone call, not a chat
- Use Claude streaming to start TTS before the full response is ready
- Maintain conversation history but window to last 10 turns to control context size
- NEVER mock Claude in integration tests — the response quality IS the test

## Turn Management
- Detect end-of-speech with silence threshold (e.g., 1.5 seconds)
- Handle interruptions: if customer speaks while TTS is playing, stop TTS and listen
- Log every state transition (greeting → listening → processing → speaking → listening)

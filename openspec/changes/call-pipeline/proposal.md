## Why

With providers implemented (Change 1), we need an orchestration layer that connects them into a working audio loop: customer speaks → STT transcribes → Claude responds → TTS synthesizes → customer hears. Without this pipeline, the providers are isolated components that can't work together. The pipeline also needs turn management so the agent knows when to listen, when to process, and when to speak.

## What Changes

- Create `CallPipeline` class that orchestrates STT → ConversationAgent → TTS flow
- Implement state machine for call states (greeting → listening → processing → speaking)
- Add turn management: VAD-based end-of-speech detection, barge-in (stop TTS when customer interrupts)
- Add structured logging for every state transition
- Add Level 1 (audio_loop) integration tests

## Capabilities

### New Capabilities
- `call-pipeline`: Orchestrates the full audio loop — receives audio, transcribes, generates response, synthesizes speech, sends back audio
- `turn-management`: Manages conversation turns — detects end-of-speech, handles barge-in/interruptions, controls state transitions

### Modified Capabilities

## Impact

- **Code**: new `src/pipeline.py` (or `src/call_pipeline.py`)
- **Dependencies**: `structlog` already in pyproject.toml
- **Integration**: connects `ConversationAgent` with STT/TTS/Telephony providers
- **Tests**: new Level 1 tests under `tests/` using real Soniox + Google TTS (no Twilio needed)

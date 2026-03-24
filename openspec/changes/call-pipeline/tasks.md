## 1. State Machine

- [ ] 1.1 Create `src/state.py` — `CallState` enum (GREETING, LISTENING, PROCESSING, SPEAKING, ENDED) and transition validation
- [ ] 1.2 Add structlog state transition logging with previous state, new state, timestamp, trigger reason

## 2. Pipeline Core

- [ ] 2.1 Create `src/pipeline.py` — `CallPipeline` class with constructor taking STT, TTS, Telephony providers + ConversationAgent
- [ ] 2.2 Implement `_stt_loop()` async task — read audio from telephony, send to STT, put transcripts on `stt_queue`
- [ ] 2.3 Implement `_llm_loop()` async task — get transcripts from `stt_queue`, call ConversationAgent.respond(), put response on `tts_queue`
- [ ] 2.4 Implement `_tts_loop()` async task — get response text from `tts_queue`, synthesize via TTS, send audio to telephony
- [ ] 2.5 Implement `run(ctx: CallContext)` — generate greeting, start 3 tasks with asyncio.TaskGroup, handle ENDED state

## 3. Turn Management

- [ ] 3.1 Implement endpoint detection handling — when Soniox finalizes tokens after silence, transition LISTENING → PROCESSING
- [ ] 3.2 Implement barge-in detection — when STT yields speech tokens during SPEAKING, stop TTS and transition to LISTENING
- [ ] 3.3 Add asyncio.Lock for shared state access between concurrent tasks
- [ ] 3.4 Implement call termination — check `should_hangup()` after each agent response, transition to ENDED

## 4. Tests

- [ ] 4.1 Add unit test for state machine transitions and validation
- [ ] 4.2 Add Level 1 integration test: stream audio file → STT → Claude → TTS → verify audio output (requires SONIOX_API_KEY + GOOGLE credentials)

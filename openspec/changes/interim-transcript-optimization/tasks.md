## 1. Config & Types

- [x] 1.1 Add `TranscriptEvent` dataclass to `src/providers/base.py` (text: str, is_interim: bool)
- [x] 1.2 Update `STTProvider.transcribe_stream` return type to `AsyncIterator[TranscriptEvent]`
- [x] 1.3 Add interim config fields to `VoiceConfig` in `src/config.py`: `interim_enabled` (default True), `interim_min_words` (default 3), `interim_silence_ms` (default 500)
- [x] 1.4 Update `config.yaml`: `endpoint_delay_ms: 800`, add interim section

## 2. Soniox STT Interim Detection

- [x] 2.1 Refactor `transcribe_stream` receive loop: replace `async for event` with timeout-based `asyncio.wait_for` loop
- [x] 2.2 Implement interim yield logic: track last-token timestamp, yield `TranscriptEvent(is_interim=True)` when silence >= `interim_silence_ms` AND words >= `interim_min_words`
- [x] 2.3 Keep final yield on `<fin>`/`<end>` tokens as `TranscriptEvent(is_interim=False)`
- [x] 2.4 Add feature flag: when `interim_enabled=False`, skip interim logic entirely (old behavior)

## 3. Pipeline Speculative Execution

- [x] 3.1 Update `_stt_queue` type from `Queue[str]` to `Queue[TranscriptEvent]` in `pipeline.py`
- [x] 3.2 Update `_stt_loop`: pass `TranscriptEvent` to queue instead of raw str, handle barge-in with event type
- [x] 3.3 Implement speculative LLM in `_llm_loop`: on interim event, start respond() as `asyncio.Task`, store task ref + interim text
- [x] 3.4 Implement final-event handling in `_llm_loop`: if final.text == interim text, let task continue; if different, cancel task + clear TTS queue + restart with final text
- [x] 3.5 Handle edge case: final arrives without preceding interim (no-op, process normally)

## 4. Testing & Validation

- [ ] 4.1 Manual test: place call with interim enabled, verify faster first response in logs (check `first_sentence` latency_ms)
- [ ] 4.2 Manual test: place call with `interim_enabled: false`, verify old behavior unchanged
- [ ] 4.3 Manual test: speak with mid-sentence pause (>500ms), verify interim fires and cancel/retry works if speech continues

## 1. CallMetrics dataclass

- [x] 1.1 Create `src/metrics.py` — `CallMetrics` dataclass with all fields (claude tokens, tts chars, stt audio ms, twilio price, response times, barge-in count, errors)
- [x] 1.2 Add `mask_phone()` helper function (+36203911669 → +3620***1669)
- [x] 1.3 Add `calculate_costs(metrics)` function returning per-provider cost dict
- [x] 1.4 Add unit tests for CallMetrics, mask_phone, and calculate_costs

## 2. Agent returns usage data

- [x] 2.1 Modify `ConversationAgent.get_greeting()` to return `(text, usage)` tuple
- [x] 2.2 Modify `ConversationAgent.respond()` to return `(text, usage)` tuple
- [x] 2.3 Update `src/test_chat.py` to handle the new return type
- [x] 2.4 Update `tests/test_agent.py` to handle the new return type

## 3. Pipeline metrics collection

- [x] 3.1 Add `CallMetrics` parameter to `CallPipeline.__init__()` and `run()`
- [x] 3.2 In `_stt_loop()`: track `event.total_audio_proc_ms` and barge-in count on metrics
- [x] 3.3 In `_llm_loop()`: accumulate claude tokens from usage, measure response latency
- [x] 3.4 In `_tts_loop()`: accumulate `len(text)` to `metrics.tts_chars`
- [x] 3.5 In greeting: accumulate greeting usage tokens and TTS chars

## 4. CallLogger

- [x] 4.1 Create `src/logger.py` — `CallLogger` class with `save(metrics, transcript, outcome)` method
- [x] 4.2 Implement JSON file writing to `logs/calls/YYYY-MM-DD/{sid}_{name}_{time}.json`
- [x] 4.3 Implement outcome classification (completed, dropped, error, dnc)
- [x] 4.4 Add unit test: save a call log → verify JSON file created with correct structure

## 5. Call runner integration

- [x] 5.1 Wire CallMetrics into call_runner.py — create metrics at start, pass to pipeline
- [x] 5.2 Fetch Twilio price post-call: `calls(sid).fetch().price`
- [x] 5.3 Invoke CallLogger.save() after call ends, before printing transcript
- [x] 5.4 Print cost summary to console after transcript

## 1. Streaming Agent

- [ ] 1.1 Add `respond_stream()` async generator to `ConversationAgent` using `client.messages.stream()`
- [ ] 1.2 Implement `is_sentence_boundary()` helper — split on `.!?` or `,` when buffer > 40 chars
- [ ] 1.3 Yield sentence chunks from `respond_stream()`, track usage from `stream.get_final_message()`
- [ ] 1.4 Add `get_greeting_stream()` async generator (greeting also benefits from streaming)

## 2. Pipeline Integration

- [ ] 2.1 Modify `_llm_loop()` to use `respond_stream()` — put each sentence chunk on `_tts_queue`
- [ ] 2.2 Add turn-end sentinel to signal last chunk — `_tts_loop` sends mark only after sentinel
- [ ] 2.3 Update greeting in `run()` to use streaming
- [ ] 2.4 Update metrics: accumulate usage from stream, track time-to-first-sentence

## 3. Tests

- [ ] 3.1 Unit test: `is_sentence_boundary()` with various inputs
- [ ] 3.2 Integration test: `respond_stream()` yields multiple chunks for a long response

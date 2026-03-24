## 1. Response Layers

- [ ] 1.1 Create `src/response_layers.py` — `ResponseLayers` class with fast (Haiku) and deep (Opus) clients
- [ ] 1.2 Implement `_fast_ack()` — minimal prompt, Haiku, max_tokens=50, ~300ms target
- [ ] 1.3 Implement `_deep_response()` — full context, Opus streaming, returns sentence chunks
- [ ] 1.4 Implement `respond()` async generator — fires both in parallel, yields fast ack then deep chunks
- [ ] 1.5 Add heuristic to skip fast ack for simple messages (< 10 chars, greetings, yes/no)

## 2. Pipeline Integration

- [ ] 2.1 Replace `ConversationAgent` usage in pipeline with `ResponseLayers` for the LLM loop
- [ ] 2.2 Update history management — both ack and deep response recorded
- [ ] 2.3 Update metrics — track fast_ack_time_ms and deep_response_time_ms separately

## 3. Tests

- [ ] 3.1 Unit test: fast ack returns within timeout, is non-committal
- [ ] 3.2 Unit test: simple message skips fast ack

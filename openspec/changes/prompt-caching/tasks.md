## 1. Add cache_control to deep response API calls

- [x] 1.1 Add `cache_control={"type": "ephemeral"}` to `_deep_response_stream()` messages.stream() call in `src/response_layers.py`
- [x] 1.2 Add `cache_control={"type": "ephemeral"}` to `_deep_response_with_tools()` messages.create() call in `src/response_layers.py`
- [x] 1.3 Add `cache_control={"type": "ephemeral"}` to local agent research() Claude API call in `src/local_agent.py`

## 2. Cache usage tracking

- [x] 2.1 Add `cache_read_input_tokens: int = 0` and `cache_creation_input_tokens: int = 0` fields to `CallMetrics` in `src/metrics.py`
- [x] 2.2 Add `add_cache_usage(read_tokens, creation_tokens)` method to `CallMetrics`
- [x] 2.3 Extract cache usage from API responses in `response_layers.py` and pass to metrics via `_track_usage()` in pipeline
- [x] 2.4 Include cache stats in call log output (`src/logger.py` or cost calculation)

## 3. Verify and test

- [ ] 3.1 Manual test: place a multi-turn call, check logs for `cache_read_input_tokens > 0` on 2nd+ turns
- [ ] 3.2 Verify cost calculation reflects cache savings in call log

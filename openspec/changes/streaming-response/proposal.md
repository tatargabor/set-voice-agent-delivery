## Why

The agent currently waits for Claude to generate the **entire** response before starting TTS. Then TTS generates the **entire** audio before sending it. This serial processing adds 2-3 seconds of silence. By streaming Claude's response and synthesizing sentence-by-sentence, the customer hears the first words within ~1 second instead of ~4 seconds.

## What Changes

- Switch `ConversationAgent` from `messages.create()` to `messages.stream()` — yield text chunks as Claude generates them
- Add sentence boundary detection: accumulate streaming tokens until a sentence boundary (`.`, `!`, `?`, `,` with sufficient length) then send to TTS
- Modify `_llm_loop` and `_tts_loop` to work with streaming: LLM yields sentence chunks, TTS processes them in sequence
- Return usage data from the streaming response (available at stream end)

## Capabilities

### New Capabilities
- `streaming-llm-tts`: Stream Claude responses sentence-by-sentence through TTS for sub-second first-word latency

### Modified Capabilities

## Impact

- **Code**: modify `src/agent.py` (streaming API), modify `src/pipeline.py` (sentence chunking, streaming LLM→TTS flow)
- **No new dependencies**
- **Metrics**: response_time_ms now measures time to first sentence, not full response

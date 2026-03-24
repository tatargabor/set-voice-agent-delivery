## Context

Currently `ConversationAgent.respond()` uses `client.messages.create()` which blocks until the full response is ready. The Anthropic SDK supports `client.messages.stream()` which yields text delta events as they're generated.

Google TTS is not truly streaming (returns full audio), but we can call it per-sentence to overlap generation.

## Goals / Non-Goals

**Goals:**
- Stream Claude response token-by-token
- Detect sentence boundaries and send each sentence to TTS immediately
- Customer hears first words within ~1 second of Claude starting to generate
- Maintain usage tracking (tokens available at stream end)

**Non-Goals:**
- True word-level TTS streaming (Google TTS doesn't support it)
- Changing TTS provider
- Changing the fast/deep layer architecture (that's a separate change)

## Decisions

### 1. Streaming API usage

```python
async with client.messages.stream(...) as stream:
    async for text in stream.text_stream:
        # accumulate into sentence buffer
        buffer += text
        if is_sentence_boundary(buffer):
            yield buffer.strip()
            buffer = ""
    # After stream ends:
    usage = stream.get_final_message().usage
```

### 2. Sentence boundary detection

Split on sentence-ending punctuation (`. ! ?`) and also on commas when the buffer is long enough (>40 chars) — Hungarian sentences tend to be long with many clauses.

```python
def is_sentence_boundary(text: str) -> bool:
    if not text.strip():
        return False
    last_char = text.rstrip()[-1]
    if last_char in '.!?':
        return True
    if last_char == ',' and len(text.strip()) > 40:
        return True
    return False
```

### 3. Pipeline flow change

Current: `_llm_loop` puts **one full response** on `_tts_queue`
New: `_llm_loop` puts **multiple sentence chunks** on `_tts_queue`

`_tts_loop` already processes queue items one by one — no change needed there. But we need to send mark only after the **last** chunk.

Solution: use a sentinel value to signal "last chunk of this turn":

```python
# In _llm_loop:
for sentence in agent.respond_stream(ctx, text):
    await self._tts_queue.put(sentence)
await self._tts_queue.put(TURN_END_SENTINEL)

# In _tts_loop:
# Send mark only when sentinel is received
```

### 4. Agent API change

`respond()` stays for backward compat. Add `respond_stream()` as async generator:

```python
async def respond_stream(self, ctx, text) -> AsyncGenerator[str, None]:
    # yields sentence chunks
    # after generator exhaustion, self.last_usage has the token counts
```

## Risks / Trade-offs

- **[Risk] Short sentences may sound choppy** → Mitigation: minimum buffer length before yielding, and Hungarian comma-splitting helps
- **[Trade-off] Google TTS called multiple times per turn** → More API calls but each is small and fast. Cost increase negligible ($4/1M chars regardless of call count)

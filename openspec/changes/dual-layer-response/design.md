## Context

After `streaming-response` lands, Claude responses stream sentence-by-sentence. But there's still a ~1-2 sec gap before the first token arrives. The dual-layer approach fills this gap.

## Goals / Non-Goals

**Goals:**
- Fast ack within ~300ms of receiving customer speech
- Deep response within ~3-5 sec (can use tools in future)
- Smooth handoff: fast ack plays, then deep response follows naturally

**Non-Goals:**
- Tool_use in deep layer (that's `deep-agent-tools`)
- Project context loading (that's `project-context-loader`)

## Decisions

### 1. ResponseLayers orchestrator

New class `ResponseLayers` that manages both layers:

```python
class ResponseLayers:
    def __init__(self):
        self.fast = AsyncAnthropic()   # Haiku
        self.deep = AsyncAnthropic()   # Opus

    async def respond(self, ctx, customer_text) -> AsyncGenerator[str, None]:
        # 1. Fire both in parallel
        fast_task = asyncio.create_task(self._fast_ack(ctx, customer_text))
        deep_task = asyncio.create_task(self._deep_response(ctx, customer_text))

        # 2. Yield fast ack immediately
        fast_text = await fast_task
        yield fast_text

        # 3. Yield deep response sentences
        deep_sentences = await deep_task
        for sentence in deep_sentences:
            yield sentence
```

### 2. Fast Layer prompt

Minimal context, minimal tokens:

```
System: "Röviden nyugtázd amit az ügyfél mondott. 1 mondat max. Magyarul."
User: "{customer_text}"
```

Model: `claude-haiku-4-5`, max_tokens: 50

### 3. Deep Layer prompt

Full context (project info, conversation history):

```
System: "{full system prompt with project context}"
Messages: {full history}
User: "{customer_text}"
```

Model: `claude-opus-4-6`, max_tokens: 300, streaming

### 4. History management

- Fast ack goes into history as `assistant` message
- Deep response goes into history as `assistant` message (appended)
- Customer sees it as one continuous agent response

### 5. When NOT to use dual-layer

Simple responses (greetings, farewells) don't need deep analysis. Heuristic: if the customer text is < 10 chars or is a greeting/farewell, skip the deep layer and just use fast.

## Risks / Trade-offs

- **[Risk] Fast ack contradicts deep response** → Mitigation: fast ack only acknowledges, never commits ("Értem" not "Igen, megcsináljuk")
- **[Risk] Awkward pause between fast ack and deep response** → Mitigation: streaming deep response fills the gap naturally
- **[Trade-off] Double API cost per turn** → Haiku is ~$0.001/turn, negligible

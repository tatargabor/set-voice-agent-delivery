## Context

After Change 1, we have concrete providers (Soniox STT, Google TTS, Twilio). The `ConversationAgent` handles text-to-text conversation with Claude. We need a pipeline that bridges audio ↔ text and manages the conversation flow.

```
┌──────────┐    audio    ┌──────────┐   text    ┌──────────┐   text    ┌──────────┐   audio   ┌──────────┐
│  Twilio  │───────────▶│  Soniox  │─────────▶│  Claude  │─────────▶│  Google  │──────────▶│  Twilio  │
│ (inbound)│  mulaw 8k  │   STT    │ hungarian │  Agent   │ hungarian │   TTS    │ mulaw 8k │(outbound)│
└──────────┘            └──────────┘           └──────────┘           └──────────┘          └──────────┘
```

## Goals / Non-Goals

**Goals:**
- Orchestrate the full STT → Claude → TTS loop as an async pipeline
- Manage call states with clear transitions and logging
- Handle barge-in (customer interrupts while TTS is playing)
- Use VAD/endpoint detection from Soniox to know when customer stops speaking

**Non-Goals:**
- Webhook server setup (Change 3)
- Call placement / hangup logic (Change 3)
- DNC / legal hours checks (Change 3)
- Call script loading (Change 3)

## Decisions

### 1. State machine with 4 states

```
          ┌─────────────────────────────────────┐
          │                                     │
          ▼                                     │
    ┌──────────┐     STT ready      ┌──────────────┐
    │ GREETING │──────────────────▶│   LISTENING   │◀─────┐
    └──────────┘                   └──────────────┘      │
          │                              │                │
          │                    endpoint  │                │
          │                    detected  │                │
          │                              ▼                │
          │                     ┌──────────────┐          │
          │                     │  PROCESSING  │          │
          │                     └──────────────┘          │
          │                              │                │
          │                     Claude   │                │
          │                     responds │                │
          │                              ▼                │
          │                     ┌──────────────┐          │
          │                     │   SPEAKING   │──────────┘
          │                     └──────────────┘   TTS done
          │                              │
          │                    should_    │
          │                    hangup?    │
          │                              ▼
          │                     ┌──────────────┐
          └────────────────────▶│   ENDED      │
                                └──────────────┘
```

States: `GREETING`, `LISTENING`, `PROCESSING`, `SPEAKING`, `ENDED`

Every transition is logged with structlog.

### 2. Barge-in handling

When customer speaks during `SPEAKING` state:
1. Stop TTS audio output immediately
2. Transition to `LISTENING`
3. Feed the new audio into STT

Detection: if STT yields non-empty tokens while state is `SPEAKING`, trigger barge-in.

### 3. Async task architecture

Three concurrent async tasks running during a call:

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(self._stt_loop())       # audio in → transcript events
    tg.create_task(self._llm_loop())       # transcript → Claude response
    tg.create_task(self._tts_loop())       # response text → audio out
```

Communication via `asyncio.Queue`:
- `stt_queue`: STT loop puts transcripts, LLM loop gets them
- `tts_queue`: LLM loop puts responses, TTS loop gets them

### 4. File structure

```
src/
├── pipeline.py          # CallPipeline class, state machine, async task orchestration
├── state.py             # CallState enum, state transition logic
```

## Risks / Trade-offs

- **[Risk] Race conditions between tasks** → Mitigation: single state variable protected by asyncio.Lock, queues for inter-task communication
- **[Risk] Barge-in detection lag** → Mitigation: STT runs continuously even during SPEAKING state, detect interruption within ~200ms of speech onset
- **[Trade-off] Three separate tasks vs single loop** → More complex but allows true streaming (TTS can start before Claude finishes full response)

## Context

We investigated the exact API responses from each provider:
- **Twilio**: `calls(sid).fetch()` returns `price` (USD), `duration` (sec), timestamps
- **Claude**: `response.usage.input_tokens`, `response.usage.output_tokens` — exact counts per request
- **Google TTS**: no usage field — we count `len(text)` ourselves
- **Soniox STT**: `event.total_audio_proc_ms` gives processed audio milliseconds; `token.start_ms/end_ms` for timing

Pricing confirmed:
- Twilio: varies (~$0.063 for 54 sec Hungarian call)
- Claude Sonnet: $3/M input, $15/M output tokens
- Google TTS: $4/1M chars (Standard)
- Soniox STT: ~$0.002/min ($0.12/hour)

## Goals / Non-Goals

**Goals:**
- Log every call to a JSON file with full transcript, costs, and metrics
- Calculate exact per-provider costs from API data
- Mask PII (phone numbers) in logs
- Make logs grep-friendly (filesystem-based, one file per call)

**Non-Goals:**
- Database storage (user explicitly wants filesystem)
- Real-time dashboard or analytics UI
- Call recording (audio files) — only text transcript
- Aggregation/reporting queries (grep is enough for now)

## Decisions

### 1. Storage: JSON files organized by date

```
logs/calls/
├── 2026-03-24/
│   ├── CA5c225f_gabor_08-38.json
│   └── CAfca943_gabor_08-34.json
└── 2026-03-25/
    └── ...
```

Filename: `{call_sid_short}_{customer_name_slug}_{HH-MM}.json`

**Why not SQLite:** User preference for simplicity. JSON files are grep-able, human-readable, and zero-dependency.

### 2. CallMetrics — mutable accumulator during call

```python
@dataclass
class CallMetrics:
    call_id: str
    timestamp_start: datetime
    timestamp_end: datetime | None
    customer_name: str
    script_name: str
    phone_masked: str

    # Claude usage (accumulated across all requests)
    claude_input_tokens: int = 0
    claude_output_tokens: int = 0
    claude_requests: int = 0

    # Google TTS (accumulated chars)
    tts_chars: int = 0

    # Soniox STT (from event.total_audio_proc_ms)
    stt_audio_ms: int = 0

    # Twilio (fetched post-call)
    twilio_price: float | None = None
    twilio_duration_sec: int | None = None

    # Performance
    response_times_ms: list[int]  # per-turn latency
    barge_in_count: int = 0
    turn_count: int = 0

    # Errors
    errors: list[dict] = field(default_factory=list)
```

### 3. Where metrics are collected

| Metric | Where collected | How |
|--------|----------------|-----|
| Claude tokens | `ConversationAgent.respond()` / `get_greeting()` | Return `response.usage` alongside text |
| TTS chars | `_tts_loop()` in pipeline | `metrics.tts_chars += len(text)` before synthesize |
| STT audio ms | `_stt_loop()` in pipeline | Track `event.total_audio_proc_ms` from last event |
| Response latency | `_llm_loop()` in pipeline | `time.time()` before/after `agent.respond()` |
| Barge-in count | `_stt_loop()` in pipeline | Increment on barge-in detection |
| Twilio price | `call_runner.py` after hangup | `calls(sid).fetch().price` |

### 4. Agent returns usage data

Change `ConversationAgent.respond()` and `get_greeting()` to return a tuple `(text, usage)` instead of just `text`. The `usage` is the Anthropic `Usage` object.

### 5. Cost calculation

```python
def calculate_costs(metrics: CallMetrics) -> dict:
    return {
        "twilio": abs(metrics.twilio_price) if metrics.twilio_price else 0,
        "claude": (metrics.claude_input_tokens * 3 + metrics.claude_output_tokens * 15) / 1_000_000,
        "google_tts": metrics.tts_chars * 4 / 1_000_000,
        "soniox_stt": (metrics.stt_audio_ms / 1000 / 60) * 0.002,
    }
```

### 6. PII masking

Phone numbers: `+36203911669` → `+3620***1669` (keep country code + first 2 + last 4).

Transcript is NOT masked (needed for quality review). The `logs/` directory is already gitignored and should be access-controlled in production.

## Risks / Trade-offs

- **[Risk] Agent API change (returning tuple)** → Mitigation: update all callers (pipeline, test_chat, tests). Small surface area.
- **[Trade-off] No audio recording** → Transcript only. Audio recording would need encrypted storage and retention policy per call-safety rules. Out of scope for now.
- **[Trade-off] Twilio price fetch is a separate API call after hangup** → Small latency, but the call is already over so it doesn't matter.

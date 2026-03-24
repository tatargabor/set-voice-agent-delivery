## Why

The voice agent can place calls but there's no record of what happened. We can't answer basic questions: how much did a call cost? What was said? Did it succeed? We need a logging system that saves every call's metadata, transcript, costs, and performance metrics to JSON files for later analysis.

## What Changes

- Create `CallMetrics` dataclass that collects metrics during a call (token counts, char counts, audio ms, timestamps)
- Modify `ConversationAgent` to return usage data (input/output tokens) alongside responses
- Modify pipeline loops to feed metrics into `CallMetrics` as they run
- Create `CallLogger` that writes a JSON file per call to `logs/calls/YYYY-MM-DD/`
- Fetch Twilio call price post-call and include in the log
- Mask phone numbers in logs (PII protection)
- Calculate per-provider costs: Twilio (from API), Claude ($3/$15 per M tokens), Google TTS ($4/1M chars), Soniox STT ($0.002/min from audio_proc_ms)

## Capabilities

### New Capabilities
- `call-metrics`: Collect per-call usage data (Claude tokens, TTS chars, STT audio ms, Twilio duration/price) during pipeline execution
- `call-logger`: Write structured JSON log per call to filesystem with metadata, transcript, costs, performance, and errors

### Modified Capabilities

## Impact

- **Code**: new `src/metrics.py`, `src/logger.py`; modify `src/agent.py` (return usage), `src/pipeline.py` (feed metrics), `src/call_runner.py` (invoke logger)
- **Filesystem**: `logs/calls/` directory (already gitignored)
- **No new dependencies** — only stdlib json, pathlib, datetime

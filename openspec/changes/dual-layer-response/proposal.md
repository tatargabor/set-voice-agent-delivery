## Why

Even with streaming, Claude Sonnet/Opus takes 1-2 seconds to start generating. During this silence the customer wonders if the call dropped. A fast acknowledgment layer (Haiku, ~200ms) fills this gap with natural responses like "Értem, megnézem!" while a deep layer (Opus) works on the real answer in the background.

This is how humans work too: you say "hmm, good question" while thinking, then give the real answer.

## What Changes

- Add a Fast Layer: Haiku model generates immediate acknowledgment (~200ms) with minimal context
- Add a Deep Layer: Opus model generates the substantive response with full context and tools (future)
- Modify pipeline to orchestrate: Fast ack → TTS immediately → Deep response → TTS when ready
- If Deep response arrives while Fast ack is still playing, queue it after

## Capabilities

### New Capabilities
- `fast-ack-layer`: Immediate acknowledgment via Haiku before the real answer
- `deep-response-layer`: Substantive response via Opus running in parallel with fast ack

### Modified Capabilities

## Impact

- **Code**: new `src/response_layers.py`, modify `src/pipeline.py` (dual-layer orchestration)
- **Dependencies**: none new (same Anthropic API, different model parameter)
- **Cost**: adds ~$0.001 per turn for Haiku ack (negligible)
- **Prereq**: `streaming-response` should land first (streaming TTS infra reused)

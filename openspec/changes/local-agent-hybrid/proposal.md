## Why

The current tool_use approach sends every tool call as an API roundtrip (Claude API → local execution → Claude API), accumulating 34K+ input tokens and $0.12/call in Claude costs for a 4-minute call. A local agent subprocess can batch multiple file reads and searches into a single research session, returning one consolidated answer — fewer API calls, lower cost, and the ability to do deeper multi-step investigation. The system should support both modes (tool_use for simple lookups, local agent for deep research) configurable per-deployment.

## What Changes

- Add a local agent runner (`src/local_agent.py`) that spawns a per-call Claude subprocess with direct filesystem access
- The agent gets the project_dir, a question, and cached context from previous calls — it investigates autonomously and returns a concise answer
- Add a context cache (`src/agent_cache.py`) that persists project investigation results between calls (file index, spec summaries, key findings) so repeat questions are instant
- Add configuration to choose research mode: `tool_use` (existing), `local_agent`, or `auto` (simple questions → tool_use, complex → local agent)
- Modify `ResponseLayers` to route deep responses through the configured research mode

## Capabilities

### New Capabilities
- `local-agent-research`: Per-call local agent that investigates the project filesystem autonomously and returns a concise voice-ready answer, with session caching between calls
- `research-mode-config`: Configuration to select research strategy (tool_use, local_agent, auto) per deployment or per project

### Modified Capabilities

## Impact

- **Code**: new `src/local_agent.py`, `src/agent_cache.py`, modify `src/response_layers.py` (routing), modify `src/webhook.py` (config)
- **Dependencies**: anthropic SDK (already present) — no new deps
- **Cost**: local agent uses ~1-2 Claude API calls per question vs 3-5 for tool_use loop, estimated 50-70% Claude cost reduction for complex questions
- **Prereq**: `deep-agent-tools` must be complete (provides tool definitions reused by local agent)

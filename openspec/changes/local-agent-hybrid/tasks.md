## 0. Central Config

- [x] 0.1 Create `config.yaml` with models, voice, research, and projects_dir settings
- [x] 0.2 Add `AppSettings` pydantic model to `src/config.py` — loads config.yaml, falls back to defaults
- [x] 0.3 Replace hardcoded values in `ResponseLayers` (model names, max_tokens, max_sentences) with config
- [x] 0.4 Replace hardcoded values in `soniox_stt.py` (endpoint_delay) with config
- [x] 0.5 Replace hardcoded `PROJECTS_DIR` env var in `webhook.py` with config
- [x] 0.6 ~~.env.example~~ — config.yaml is self-documented with comments

## 1. Context Cache

- [x] 1.1 Create `src/agent_cache.py` — `AgentCache` dataclass (file_index, spec_summaries, change_summaries, findings) + global cache dict keyed by project_dir
- [x] 1.2 Implement `get_or_create_cache(project_dir)` — returns existing cache or populates new one (list files, read spec names, read change names+status)
- [x] 1.3 Implement `cache.add_finding(finding)` — append a key finding for future calls

## 2. Local Agent

- [x] 2.1 Create `src/local_agent.py` — async `research(question, project_dir, cache)` function with own system prompt, tool_use loop (max 3 iterations), 10s timeout
- [x] 2.2 Agent system prompt: research-focused, max 2 sentences, voice-ready output, uses cache context
- [x] 2.3 Agent injects cache (file_index, spec_summaries, findings) into system prompt so it doesn't need to re-discover basic info
- [x] 2.4 Agent max_tokens=100, tool results truncated to 1000 chars
- [x] 2.5 After research, extract and cache key findings from the answer

## 3. Research Mode Routing

- [x] 3.1 Read `research.mode` from config (`tool_use` | `local_agent` | `auto`, default `tool_use`)
- [x] 3.2 Implement `_is_research_question(text)` heuristic for auto mode
- [x] 3.3 Add `_deep_response_with_agent()` method in `ResponseLayers` — calls `research()`, splits result into sentences, applies 3-sentence limit
- [x] 3.4 Update `_collect_deep()` in `ResponseLayers.respond()` to route based on RESEARCH_MODE
- [x] 3.5 Add `research_mode` field to call log output

## 4. Tests

- [x] 4.1 Unit test: AgentCache populates file_index and spec_summaries from a tmp project
- [x] 4.2 Unit test: get_or_create_cache returns same cache on second call
- [x] 4.3 Unit test: _is_research_question detects research keywords
- [x] 4.4 Unit test: RESEARCH_MODE defaults to tool_use

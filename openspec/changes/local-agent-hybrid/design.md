## Context

The current `deep-agent-tools` implementation uses Anthropic tool_use API for project investigation during live calls. Each tool call is a full API roundtrip: Claude decides → we execute locally → send result back → Claude decides again. A 4-minute call with 10 tool calls costs $0.12 in Claude tokens (34K input tokens from repeated history+results).

The user wants a hybrid system: simple lookups use tool_use (fast, cheap), while complex research spawns a local agent subprocess that does autonomous multi-step investigation and returns one consolidated answer.

## Goals / Non-Goals

**Goals:**
- Local agent subprocess that investigates a project directory and returns a concise answer
- Per-project context cache that persists between calls (avoid re-indexing on every call)
- Configurable research mode: `tool_use`, `local_agent`, or `auto`
- Lower Claude API cost for complex questions (target: 50-70% reduction)

**Non-Goals:**
- Code modification during calls (read-only, same as tool_use)
- Using Claude Code CLI as the agent (too heavy — we build a lightweight agent loop)
- Real-time streaming from the local agent (it returns a complete answer)
- Cross-project investigation (agent is scoped to one project_dir)

## Decisions

### 1. Local agent architecture

The local agent is a single async function (`research()`) that runs the Anthropic tool_use loop internally — same tools as `agent_tools.py`, but in a tight local loop without voice pipeline overhead.

```
async def research(question: str, project_dir: Path, cache: AgentCache) -> str:
    """Investigate and return a concise voice-ready answer."""
```

Key difference from tool_use in ResponseLayers: the agent manages its own message history (not the call's conversation history), so input tokens stay small.

**Why not a subprocess?** A subprocess adds process spawn overhead (~500ms), IPC complexity, and error handling burden. An async function in the same process is simpler and faster, while still being logically isolated.

### 2. Context cache

Per-project cache stored in memory (dict keyed by project_dir), populated lazily:

```python
class AgentCache:
    project_dir: Path
    file_index: list[str]        # All file paths (populated on first call)
    spec_summaries: dict          # spec name → one-line summary
    change_summaries: dict        # change name → status + summary
    findings: list[str]           # Key findings from previous questions
    last_updated: datetime
```

Cache lifetime: entire server process (reset on restart). Cache is populated incrementally — first call indexes files and specs, subsequent calls add findings.

**Why not disk cache?** The server restarts infrequently, and stale disk cache is worse than a fresh re-index. In-memory is simpler and always fresh.

### 3. Central config.yaml

Application settings move from scattered env vars and hardcoded defaults to a single `config.yaml`:

```yaml
# config.yaml
models:
  fast: claude-haiku-4-5        # Fast ack layer
  deep: claude-sonnet-4-6       # Deep response
  agent: claude-sonnet-4-6      # Local agent research

voice:
  max_sentences: 3              # Max sentences per response
  max_tokens_tool_use: 150      # Deep layer with tool_use
  max_tokens_agent: 100         # Local agent response
  max_tokens_stream: 300        # Streaming (no tools)
  endpoint_delay_ms: 1200       # Soniox silence detection

research:
  mode: auto                    # tool_use | local_agent | auto
  agent_timeout_sec: 10
  agent_max_iterations: 3
  tool_timeout_sec: 15

projects_dir: /home/tg/code2    # Where to find customer projects
```

API keys stay in `.env` (security — never committed). `config.yaml` is committed and shared.

Loaded once at startup via `load_app_config()` → `AppSettings` pydantic model. Accessed globally.

### 4. Research mode routing

Three modes, configured via `config.yaml` `research.mode`:

| Mode | Behavior |
|------|----------|
| `tool_use` | Current behavior — Claude tool_use loop in ResponseLayers (default) |
| `local_agent` | Always use local agent for non-simple questions |
| `auto` | Heuristic: short questions → tool_use, questions mentioning files/specs/code → local agent |

The `auto` heuristic checks for keywords: "fájl", "kód", "spec", "change", "design", "keress", "nézd meg", "mi van a", "hogyan van implementálva".

### 4. Agent system prompt

The local agent gets a research-focused system prompt (different from the voice agent prompt):

```
Te egy projekt kutató agent vagy. Feladatod: a megadott kérdést megválaszolni
a projekt fájljai alapján. Használd a tool-okat a kereséshez.

Szabályok:
- Max 2 mondatban válaszolj — az eredményed telefonon lesz felolvasva
- Foglald össze a lényeget, ne olvass fel fájlokat szó szerint
- Ha nem találsz választ, mondd meg őszintén
```

### 5. Integration with ResponseLayers

```
ResponseLayers.respond()
    ├── _is_simple() → streaming deep (no tools, no agent)
    │
    ├── RESEARCH_MODE == "tool_use"
    │   └── _deep_response_with_tools()  (existing)
    │
    ├── RESEARCH_MODE == "local_agent"
    │   └── _deep_response_with_agent()  (new)
    │
    └── RESEARCH_MODE == "auto"
        ├── _is_research_question() → local agent
        └── else → tool_use
```

### 6. Timeout and cost control

- Local agent: 10 second total timeout, max 3 tool iterations
- Tool results truncated to 1000 chars (agent doesn't need full files)
- Agent max_tokens: 100 (forced brevity)

## Risks / Trade-offs

- **[Risk] Agent gives wrong/hallucinated answer** → Mitigation: agent prompt emphasizes honesty ("ha nem találsz választ, mondd meg"), and findings cache lets us improve over time
- **[Risk] Cache becomes stale if project changes during call** → Acceptable: calls are short (minutes), project won't change mid-call
- **[Trade-off] Not a real subprocess** → Simpler, faster, but shares memory/event loop with voice pipeline. If agent blocks, voice is affected. Mitigation: 10s hard timeout
- **[Trade-off] In-memory cache lost on restart** → Re-indexing is fast (<100ms), acceptable tradeoff vs disk cache complexity

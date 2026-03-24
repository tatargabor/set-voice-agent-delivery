## Context

After `dual-layer-response` and `project-context-loader` land, the Deep Layer has project context but can only answer from what was pre-loaded. With tool_use, it becomes an agent that can investigate on-demand.

## Goals / Non-Goals

**Goals:**
- Deep Layer can read files, search code, check designs during a live call
- Can create openspec changes from customer requests
- Tool execution sandboxed to the customer's project directory

**Non-Goals:**
- Code modification during call (read-only)
- External API calls from tools (no deploy, no webhook)
- Using Claude Code CLI as a subprocess (too heavy — use Anthropic tool_use API directly)

## Decisions

### 1. Tool definitions

Five tools using Anthropic tool_use format:

| Tool | Input | Output | Use case |
|------|-------|--------|----------|
| `file_read` | `path: str` | File contents (max 2000 chars) | "What color is the header?" |
| `grep_search` | `pattern: str, path: str` | Matching lines | "Where is the contact form?" |
| `openspec_read` | `name: str` | Spec or change content | "What's the status of my request?" |
| `openspec_create_change` | `name: str, description: str` | Confirmation | "Create a task for this" |
| `design_check` | `component: str` | Design tokens for component | "What does the navbar look like?" |

### 2. Tool execution is sandboxed

All file paths are resolved relative to `project_dir`. Absolute paths and `..` traversal are rejected.

### 3. Tool_use loop in Deep Layer

```python
async def deep_response_with_tools(self, ctx, text, project_dir):
    messages = [...]
    while True:
        response = await client.messages.create(
            model="claude-opus-4-6",
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        if response.stop_reason == "tool_use":
            # Execute tool, add result to messages, continue
            tool_results = execute_tools(response, project_dir)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            # Final text response
            return response.content[0].text
```

### 4. Timeout

Tool_use loop has a 15 second total timeout. If exceeded, return whatever partial answer is available.

### 5. File structure

```
src/
├── agent_tools.py      # Tool definitions + sandboxed execution
├── response_layers.py  # Updated with tool_use loop
```

## Risks / Trade-offs

- **[Risk] Tool execution takes too long** → Mitigation: 15s timeout, fast ack layer covers the wait
- **[Risk] Tool gives wrong info** → Mitigation: agent verifies and phrases answers carefully ("I see the file shows X")
- **[Trade-off] Not using Claude Code CLI** → Simpler, lighter, but less capable. Claude Code subprocess would add latency and complexity. API tool_use is sufficient for read operations.
- **[Security] Sandbox escape** → Path validation: reject absolute paths, `..`, symlinks outside project_dir

## Why

The Deep Layer (Opus) from `dual-layer-response` can only answer from its pre-loaded context. But real customer questions often need live investigation: "can you check if my contact form works?", "what color is the header?", "create a task for this change." With tool_use, the deep layer becomes an actual agent that can read files, search code, check designs, and create work items — all while on the phone.

## What Changes

- Define tools for the Deep Layer Claude API call using Anthropic tool_use:
  - `file_read(path)` — read a file from the customer's project repo
  - `grep_search(pattern, path)` — search code in the repo
  - `openspec_read(spec_name)` — read a specific spec or change
  - `openspec_create_change(name, description)` — create a new change/task from customer request
  - `design_check(component_name)` — look up a component in design-snapshot.md
- Implement tool execution loop: Claude calls tool → we execute → return result → Claude continues
- Add tool results to the deep response that gets spoken to the customer

## Capabilities

### New Capabilities
- `deep-agent-toolbox`: Tool_use integration for the Deep Layer — file read, code search, openspec management, design lookup during live calls

### Modified Capabilities

## Impact

- **Code**: new `src/agent_tools.py` (tool definitions + execution), modify `src/response_layers.py` (tool_use loop in deep layer)
- **Security**: tool execution is sandboxed to the customer's project_dir only
- **Prereq**: `dual-layer-response` and `project-context-loader` must land first

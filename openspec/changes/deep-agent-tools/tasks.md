## 1. Tool Definitions

- [x] 1.1 Create `src/agent_tools.py` — define 4 read-only tools in Anthropic tool_use format (file_read, grep_search, openspec_read, design_check)
- [x] 1.2 Implement `file_read()` — read file relative to project_dir, max 2000 chars
- [x] 1.3 Implement `grep_search()` — search pattern in project_dir, return matching lines
- [x] 1.4 Implement `openspec_read()` — read spec or change content
- [x] 1.5 ~~openspec_create_change~~ — SKIPPED (read-only per user decision)
- [x] 1.6 Implement `design_check()` — extract component section from design-snapshot.md
- [x] 1.7 Implement path sandboxing — reject absolute paths, `..` traversal, symlinks outside project_dir

## 2. Tool Execution Loop

- [x] 2.1 Add tool_use loop to `ResponseLayers._deep_response_with_tools()` — handle tool_use stop_reason, execute, return results
- [x] 2.2 Add 15 second total timeout for tool loop
- [x] 2.3 Add tool call logging to metrics (tool name, execution time)

## 3. Tests

- [x] 3.1 Unit test: file_read returns content, rejects path traversal
- [x] 3.2 Unit test: grep_search returns matching lines
- [x] 3.3 Unit test: path sandboxing blocks `../../etc/passwd`

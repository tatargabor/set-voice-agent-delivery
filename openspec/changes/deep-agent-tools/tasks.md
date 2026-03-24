## 1. Tool Definitions

- [ ] 1.1 Create `src/agent_tools.py` — define 5 tools in Anthropic tool_use format (file_read, grep_search, openspec_read, openspec_create_change, design_check)
- [ ] 1.2 Implement `file_read()` — read file relative to project_dir, max 2000 chars
- [ ] 1.3 Implement `grep_search()` — search pattern in project_dir, return matching lines
- [ ] 1.4 Implement `openspec_read()` — read spec or change content
- [ ] 1.5 Implement `openspec_create_change()` — create new change via openspec CLI
- [ ] 1.6 Implement `design_check()` — extract component section from design-snapshot.md
- [ ] 1.7 Implement path sandboxing — reject absolute paths, `..` traversal, symlinks outside project_dir

## 2. Tool Execution Loop

- [ ] 2.1 Add tool_use loop to `ResponseLayers._deep_response()` — handle tool_use stop_reason, execute, return results
- [ ] 2.2 Add 15 second total timeout for tool loop
- [ ] 2.3 Add tool call logging to metrics (tool name, execution time)

## 3. Tests

- [ ] 3.1 Unit test: file_read returns content, rejects path traversal
- [ ] 3.2 Unit test: grep_search returns matching lines
- [ ] 3.3 Unit test: path sandboxing blocks `../../etc/passwd`

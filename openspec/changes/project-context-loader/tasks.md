## 1. Project Context

- [ ] 1.1 Create `src/project_context.py` — `ProjectContext` dataclass + `load_project_context()` function
- [ ] 1.2 Load README.md / CLAUDE.md as project summary (first 2000 chars)
- [ ] 1.3 Load openspec/specs/ — list spec names + first requirement from each
- [ ] 1.4 Load openspec/changes/ — list active change names + status
- [ ] 1.5 Load design-snapshot.md if exists (Design Tokens section)
- [ ] 1.6 Load previous call log — find most recent log for this customer in logs/calls/
- [ ] 1.7 Implement 4000 char truncation with priority (summary > specs > changes > design > previous call)

## 2. Integration

- [ ] 2.1 Extend call_scripts YAML schema with optional `project_dir` field
- [ ] 2.2 Update `script_loader.py` to pass project_dir through CallContext
- [ ] 2.3 Update `ConversationAgent._build_system_prompt()` to include project context
- [ ] 2.4 Wire in call_runner.py — load project context before call, pass to agent

## 3. Tests

- [ ] 3.1 Unit test: load_project_context from a test directory with sample files
- [ ] 3.2 Unit test: truncation works at 4000 chars
- [ ] 3.3 Unit test: missing project_dir gracefully skipped

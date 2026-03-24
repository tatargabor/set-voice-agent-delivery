## Why

The agent currently has zero knowledge about the customer's project — it only knows their name and "we sent a letter about their website." To give meaningful answers ("your menu is currently red, the Navbar component is at line 42"), the agent needs project context loaded before the call starts.

## What Changes

- Create `ProjectContext` loader that reads project data from a configurable project directory:
  - README.md / CLAUDE.md (project summary)
  - openspec/specs/ (capabilities and requirements)
  - openspec/changes/ (active work items)
  - design-snapshot.md (UI design tokens, if exists)
- Load previous call log for this customer (from logs/calls/) for conversation continuity
- Inject project context into the Claude system prompt
- Extend call_scripts YAML with `project_dir` field pointing to the customer's repo
- Extend CallContext with `project_summary` field

## Capabilities

### New Capabilities
- `project-context`: Load customer project data (git repo, specs, design, previous calls) into call context before the call starts

### Modified Capabilities

## Impact

- **Code**: new `src/project_context.py`, modify `src/script_loader.py` (project_dir), modify `src/agent.py` (system prompt with project context)
- **Config**: call_scripts YAML gets `project_dir` field
- **No new dependencies**

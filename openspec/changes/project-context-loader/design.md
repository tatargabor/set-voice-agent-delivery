## Context

The call script YAML already has project-related fields (website_url). We need to extend this to point to a full project directory so the agent can know specifics about the customer's work.

## Goals / Non-Goals

**Goals:**
- Load project data from a local directory before the call
- Include: project summary, specs, active changes, design tokens, previous call logs
- Inject into Claude system prompt so the agent can reference specifics

**Non-Goals:**
- Remote project access (SSH, GitHub API) — local dir only for now
- Real-time project monitoring during call

## Decisions

### 1. ProjectContext dataclass

```python
@dataclass
class ProjectContext:
    project_summary: str      # README + CLAUDE.md digest
    specs_summary: str        # openspec specs overview
    active_changes: str       # openspec active changes list
    design_tokens: str | None # design-snapshot.md if exists
    previous_call: str | None # last call log transcript for this customer
```

### 2. Loader reads from project_dir

```python
def load_project_context(project_dir: Path, customer_name: str) -> ProjectContext:
    # 1. README.md or CLAUDE.md → project_summary (first 2000 chars)
    # 2. openspec/specs/**/*.md → concatenate spec names + first lines
    # 3. openspec/changes/ → list active change names + proposals
    # 4. design-snapshot.md → design tokens section
    # 5. logs/calls/ → find last call for this customer → transcript
```

### 3. Call script YAML extension

```yaml
context:
  purpose: "..."
  variables: [...]
  project_dir: "/home/tg/code2/customer-project"  # NEW
```

### 4. System prompt injection

Append to system prompt:
```
Projekt kontextus:
- Összefoglaló: {project_summary}
- Specifikációk: {specs_summary}
- Aktív munkák: {active_changes}
- Design: {design_tokens}
- Előző hívás: {previous_call}
```

Truncate if total > 4000 chars to keep prompt manageable.

### 5. File structure

```
src/
├── project_context.py   # ProjectContext dataclass + loader
```

## Risks / Trade-offs

- **[Risk] Large project context bloats prompt** → Mitigation: 4000 char limit, summarize rather than include raw content
- **[Risk] Project dir doesn't exist** → Mitigation: graceful fallback, project_dir is optional in YAML
- **[Trade-off] Static snapshot vs live** → We load once before the call. If files change during the call, we don't see it. Acceptable for phone calls.

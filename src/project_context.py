"""Load customer project data for voice agent context."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_CONTEXT_CHARS = 4000


@dataclass
class ProjectContext:
    """Loaded project data for Claude system prompt."""
    project_summary: str = ""
    specs_summary: str = ""
    active_changes: str = ""
    design_tokens: str | None = None
    previous_call: str | None = None

    def to_prompt_section(self) -> str:
        """Format as a section for the Claude system prompt."""
        parts = []
        if self.project_summary:
            parts.append(f"Projekt összefoglaló:\n{self.project_summary}")
        if self.specs_summary:
            parts.append(f"Specifikációk:\n{self.specs_summary}")
        if self.active_changes:
            parts.append(f"Aktív munkák:\n{self.active_changes}")
        if self.design_tokens:
            parts.append(f"Design:\n{self.design_tokens}")
        if self.previous_call:
            parts.append(f"Előző hívás:\n{self.previous_call}")

        text = "\n\n".join(parts)
        if len(text) > MAX_CONTEXT_CHARS:
            text = text[:MAX_CONTEXT_CHARS] + "\n[...csonkolva]"
        return text


def load_project_context(
    project_dir: str | Path,
    customer_name: str = "",
    call_logs_dir: str | Path | None = None,
) -> ProjectContext:
    """Load project context from a local directory.

    Args:
        project_dir: Path to the customer's project directory.
        customer_name: Customer name for finding previous call logs.
        call_logs_dir: Path to call logs directory (defaults to logs/calls/).

    Returns:
        ProjectContext with loaded data, or empty if dir doesn't exist.
    """
    project_dir = Path(project_dir)
    ctx = ProjectContext()

    if not project_dir.exists():
        return ctx

    # 1. Project summary — README.md or CLAUDE.md (first 2000 chars)
    for readme in ["CLAUDE.md", "README.md"]:
        readme_path = project_dir / readme
        if readme_path.exists():
            text = readme_path.read_text(errors="ignore")[:2000]
            ctx.project_summary = text.strip()
            break

    # 2. OpenSpec specs — list names + first requirement
    specs_dir = project_dir / "openspec" / "specs"
    if specs_dir.exists():
        specs = []
        for spec_dir in sorted(specs_dir.iterdir()):
            if spec_dir.is_dir():
                spec_file = spec_dir / "spec.md"
                if spec_file.exists():
                    content = spec_file.read_text(errors="ignore")
                    # Extract first requirement name
                    req_match = re.search(r"### Requirement: (.+)", content)
                    req_name = req_match.group(1) if req_match else "?"
                    specs.append(f"- {spec_dir.name}: {req_name}")
        if specs:
            ctx.specs_summary = "\n".join(specs[:15])  # max 15 specs

    # 3. Active changes — list names + status
    changes_dir = project_dir / "openspec" / "changes"
    if changes_dir.exists():
        changes = []
        for change_dir in sorted(changes_dir.iterdir()):
            if change_dir.is_dir() and (change_dir / ".openspec.yaml").exists():
                proposal = change_dir / "proposal.md"
                summary = ""
                if proposal.exists():
                    first_line = proposal.read_text(errors="ignore").split("\n")
                    for line in first_line:
                        if line.strip() and not line.startswith("#"):
                            summary = line.strip()[:80]
                            break
                changes.append(f"- {change_dir.name}: {summary}")
        if changes:
            ctx.active_changes = "\n".join(changes[:10])

    # 4. Design snapshot
    design_path = project_dir / "design-snapshot.md"
    if design_path.exists():
        content = design_path.read_text(errors="ignore")
        # Extract Design Tokens section
        tokens_match = re.search(r"## Design Tokens\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if tokens_match:
            ctx.design_tokens = tokens_match.group(1).strip()[:500]

    # 5. Previous call log for this customer
    if call_logs_dir is None:
        call_logs_dir = Path(__file__).parent.parent / "logs" / "calls"
    call_logs_dir = Path(call_logs_dir)

    if call_logs_dir.exists() and customer_name:
        name_slug = re.sub(r"[^a-z0-9]", "", customer_name.lower())
        # Find most recent log matching customer
        matching = []
        for day_dir in sorted(call_logs_dir.iterdir(), reverse=True):
            if day_dir.is_dir():
                for log_file in sorted(day_dir.glob(f"*{name_slug}*.json"), reverse=True):
                    matching.append(log_file)
                    if len(matching) >= 1:
                        break
            if matching:
                break

        if matching:
            try:
                data = json.loads(matching[0].read_text())
                turns = data.get("transcript", [])
                lines = [f"  {t['role']}: {t['text'][:60]}" for t in turns[:6]]
                ctx.previous_call = f"Utolsó hívás ({data.get('timestamp_start', '?')[:10]}):\n" + "\n".join(lines)
            except Exception:
                pass

    return ctx

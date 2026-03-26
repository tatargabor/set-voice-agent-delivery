"""Load customer project data for voice agent context."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_CONTEXT_CHARS = 12000


@dataclass
class ProjectContext:
    """Loaded project data for Claude system prompt."""
    project_summary: str = ""
    specs_summary: str = ""
    active_changes: str = ""
    docs_content: str = ""
    design_tokens: str | None = None
    previous_call: str | None = None

    def to_prompt_section(self) -> str:
        """Format as a section for the Claude system prompt."""
        parts = []
        if self.project_summary:
            parts.append(f"Projekt összefoglaló:\n{self.project_summary}")
        if self.specs_summary:
            parts.append(f"Specifikációk (openspec):\n{self.specs_summary}")
        if self.active_changes:
            parts.append(f"Aktív munkák:\n{self.active_changes}")
        if self.docs_content:
            parts.append(f"Dokumentáció (docs/):\n{self.docs_content}")
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

    # 0. Check for cached index — if fresh, use it instead of raw loading
    project_id = project_dir.name
    try:
        from .project_indexer import read_cache, format_summary_for_prompt
        cached = read_cache(project_id, project_dir)
        if cached and cached.get("summary"):
            ctx.project_summary = format_summary_for_prompt(cached["summary"])
            # Still load previous call (not in index)
            _load_previous_call(ctx, project_dir, customer_name, call_logs_dir)
            return ctx
    except ImportError:
        pass  # Indexer not available, fall back to raw loading

    # 1. Project summary — prefer README.md, fallback to pyproject.toml description
    readme_path = project_dir / "README.md"
    pyproject_path = project_dir / "pyproject.toml"
    if readme_path.exists():
        text = readme_path.read_text(errors="ignore")[:2000]
        ctx.project_summary = text.strip()
    elif pyproject_path.exists():
        # Extract name and description from pyproject.toml
        content = pyproject_path.read_text(errors="ignore")
        name_match = re.search(r'name\s*=\s*"(.+?)"', content)
        desc_match = re.search(r'description\s*=\s*"(.+?)"', content)
        parts = []
        if name_match:
            parts.append(f"Projekt: {name_match.group(1)}")
        if desc_match:
            parts.append(desc_match.group(1))
        ctx.project_summary = "\n".join(parts)

    # 2. OpenSpec specs — load full spec content (requirements, description)
    specs_dir = project_dir / "openspec" / "specs"
    if specs_dir.exists():
        specs = []
        total_spec_chars = 0
        for spec_dir in sorted(specs_dir.iterdir()):
            if spec_dir.is_dir() and total_spec_chars < 4000:
                spec_file = spec_dir / "spec.md"
                if spec_file.exists():
                    content = spec_file.read_text(errors="ignore")
                    # Include spec name + full content (truncated per spec)
                    truncated = content[:800] if len(content) > 800 else content
                    specs.append(f"### {spec_dir.name}\n{truncated}")
                    total_spec_chars += len(truncated)
        if specs:
            ctx.specs_summary = "\n\n".join(specs)

    # 3. Active changes — load proposal + tasks status
    changes_dir = project_dir / "openspec" / "changes"
    if changes_dir.exists():
        changes = []
        total_change_chars = 0
        for change_dir in sorted(changes_dir.iterdir()):
            if change_dir.is_dir() and (change_dir / ".openspec.yaml").exists() and total_change_chars < 3000:
                parts = [f"### {change_dir.name}"]
                proposal = change_dir / "proposal.md"
                if proposal.exists():
                    prop_text = proposal.read_text(errors="ignore")[:500]
                    parts.append(prop_text)
                tasks = change_dir / "tasks.md"
                if tasks.exists():
                    tasks_text = tasks.read_text(errors="ignore")[:300]
                    parts.append(f"Feladatok:\n{tasks_text}")
                change_text = "\n".join(parts)
                changes.append(change_text)
                total_change_chars += len(change_text)
        if changes:
            ctx.active_changes = "\n\n".join(changes)

    # 4. Documentation — load all .md files from docs/
    docs_dir = project_dir / "docs"
    if docs_dir.exists():
        docs_parts = []
        total_docs_chars = 0
        for doc_file in sorted(docs_dir.rglob("*.md")):
            if total_docs_chars < 3000:
                rel_path = doc_file.relative_to(docs_dir)
                content = doc_file.read_text(errors="ignore")
                truncated = content[:1000] if len(content) > 1000 else content
                docs_parts.append(f"### {rel_path}\n{truncated}")
                total_docs_chars += len(truncated)
        if docs_parts:
            ctx.docs_content = "\n\n".join(docs_parts)

    # 6. Design snapshot
    design_path = project_dir / "design-snapshot.md"
    if design_path.exists():
        content = design_path.read_text(errors="ignore")
        # Extract Design Tokens section
        tokens_match = re.search(r"## Design Tokens\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
        if tokens_match:
            ctx.design_tokens = tokens_match.group(1).strip()[:500]

    # 7. Previous call log for this customer
    _load_previous_call(ctx, project_dir, customer_name, call_logs_dir)

    return ctx


def _load_previous_call(
    ctx: ProjectContext,
    project_dir: Path,
    customer_name: str,
    call_logs_dir: str | Path | None = None,
) -> None:
    """Load the most recent call log for this customer."""
    if call_logs_dir is None:
        call_logs_dir = Path(__file__).parent.parent / "logs" / "calls"
    call_logs_dir = Path(call_logs_dir)

    if call_logs_dir.exists() and customer_name:
        name_slug = re.sub(r"[^a-z0-9]", "", customer_name.lower())
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

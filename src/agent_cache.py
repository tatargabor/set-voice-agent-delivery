"""Per-project context cache for local agent research."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import structlog

log = structlog.get_logger()

_MAX_FINDINGS = 20


@dataclass
class AgentCache:
    """Cached project context — persists between calls within the same server process."""
    project_dir: Path
    file_index: list[str] = field(default_factory=list)
    spec_summaries: dict[str, str] = field(default_factory=dict)
    change_summaries: dict[str, str] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def add_finding(self, finding: str) -> None:
        """Add a key finding, dedup and cap at _MAX_FINDINGS."""
        if finding not in self.findings:
            self.findings.append(finding)
            if len(self.findings) > _MAX_FINDINGS:
                self.findings = self.findings[-_MAX_FINDINGS:]

    def to_context_string(self) -> str:
        """Format cache as context for agent system prompt."""
        parts = []
        if self.file_index:
            parts.append(f"Fájlok ({len(self.file_index)}):\n" + "\n".join(self.file_index[:50]))
        if self.spec_summaries:
            specs = "\n".join(f"- {k}: {v}" for k, v in self.spec_summaries.items())
            parts.append(f"Specifikációk:\n{specs}")
        if self.change_summaries:
            changes = "\n".join(f"- {k}: {v}" for k, v in self.change_summaries.items())
            parts.append(f"Change-ek:\n{changes}")
        if self.findings:
            parts.append(f"Korábbi megállapítások:\n" + "\n".join(f"- {f}" for f in self.findings))
        return "\n\n".join(parts)


# Global cache keyed by project_dir string
_cache: dict[str, AgentCache] = {}


def get_or_create_cache(project_dir: Path) -> AgentCache:
    """Return cached context for project, or populate a new one."""
    key = str(project_dir)
    if key in _cache:
        return _cache[key]

    cache = AgentCache(project_dir=project_dir)
    _populate_cache(cache)
    _cache[key] = cache
    log.info("agent_cache_created", project=key, files=len(cache.file_index),
             specs=len(cache.spec_summaries), changes=len(cache.change_summaries))
    return cache


def _populate_cache(cache: AgentCache) -> None:
    """Index files, specs, and changes from the project directory."""
    project_dir = cache.project_dir

    # File index — relative paths, skip hidden dirs and common noise
    _SKIP_DIRS = {".git", "node_modules", "__pycache__", ".next", "dist", "build", ".venv", "venv"}
    for path in project_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(project_dir)
            if not any(part in _SKIP_DIRS for part in rel.parts):
                cache.file_index.append(str(rel))

    # Spec summaries
    specs_dir = project_dir / "openspec" / "specs"
    if specs_dir.exists():
        for spec_dir in specs_dir.iterdir():
            if spec_dir.is_dir():
                spec_file = spec_dir / "spec.md"
                if spec_file.exists():
                    first_req = ""
                    for line in spec_file.read_text(errors="replace").splitlines():
                        if line.startswith("### Requirement:"):
                            first_req = line.replace("### Requirement:", "").strip()
                            break
                    cache.spec_summaries[spec_dir.name] = first_req or "(no requirements)"

    # Change summaries
    changes_dir = project_dir / "openspec" / "changes"
    if changes_dir.exists():
        for change_dir in changes_dir.iterdir():
            if change_dir.is_dir():
                proposal = change_dir / "proposal.md"
                tasks = change_dir / "tasks.md"
                summary = ""
                if proposal.exists():
                    for line in proposal.read_text(errors="replace").splitlines():
                        if line.strip() and not line.startswith("#"):
                            summary = line.strip()[:100]
                            break
                if tasks.exists():
                    content = tasks.read_text(errors="replace")
                    total = content.count("- [")
                    done = content.count("- [x]")
                    summary += f" ({done}/{total} tasks)"
                cache.change_summaries[change_dir.name] = summary or "(empty)"

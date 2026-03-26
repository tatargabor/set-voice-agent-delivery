"""Project indexer — generates Claude-summarized project context for voice calls.

Reads all docs/*.md and openspec/ files from a customer project,
sends to Claude Haiku for structured summarization, and caches the result.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from anthropic import AsyncAnthropic
import structlog

log = structlog.get_logger()

INDEXES_DIR = Path(__file__).parent.parent / "logs" / "indexes"
SUMMARIES_DIR = Path(__file__).parent.parent / "logs" / "summaries"

_MAX_RAW_CHARS = 30000

_SUMMARY_PROMPT = """Egy ügyfél projektjének teljes dokumentációját kapod. Készíts strukturált összefoglalót a projekt állapotáról.

Válaszolj CSAK a megadott JSON formátumban, semmi más szöveget ne adj hozzá:

{
  "project_name": "A projekt neve",
  "description": "1-2 mondatos leírás mit csinál a projekt",
  "modules": [
    {"name": "Modul neve", "description": "Mit csinál, milyen állapotban van"}
  ],
  "design": {
    "colors": "Fő színek ha vannak (pl. kék #2563EB, szürke háttér)",
    "font": "Betűtípus ha van",
    "style": "Általános stílus (pl. modern, minimál, corporate)"
  },
  "status": {
    "done": ["Kész elemek listája"],
    "in_progress": ["Folyamatban lévő munkák"],
    "planned": ["Tervezett fejlesztések"]
  },
  "previous_requests": ["Korábbi ügyfélkérések ha vannak"]
}

Ha egy mező nem derül ki a dokumentációból, adj üres stringet vagy üres listát.
FONTOS: Csak JSON-t adj vissza, semmi mást!"""


def _collect_source_files(project_dir: Path) -> dict[str, str]:
    """Collect all relevant source files and their content.

    Returns dict of relative_path -> content.
    """
    files: dict[str, str] = {}

    # docs/*.md (recursively)
    docs_dir = project_dir / "docs"
    if docs_dir.exists():
        for f in sorted(docs_dir.rglob("*.md")):
            rel = str(f.relative_to(project_dir))
            files[rel] = f.read_text(errors="ignore")

    # openspec/specs/**/spec.md
    specs_dir = project_dir / "openspec" / "specs"
    if specs_dir.exists():
        for spec_dir in sorted(specs_dir.iterdir()):
            if spec_dir.is_dir():
                spec_file = spec_dir / "spec.md"
                if spec_file.exists():
                    rel = str(spec_file.relative_to(project_dir))
                    files[rel] = spec_file.read_text(errors="ignore")

    # openspec/changes/*/proposal.md and tasks.md
    changes_dir = project_dir / "openspec" / "changes"
    if changes_dir.exists():
        for change_dir in sorted(changes_dir.iterdir()):
            if change_dir.is_dir():
                for fname in ["proposal.md", "tasks.md"]:
                    fpath = change_dir / fname
                    if fpath.exists():
                        rel = str(fpath.relative_to(project_dir))
                        files[rel] = fpath.read_text(errors="ignore")

    # design-snapshot.md
    design_path = project_dir / "design-snapshot.md"
    if design_path.exists():
        rel = str(design_path.relative_to(project_dir))
        files[rel] = design_path.read_text(errors="ignore")

    # README.md
    readme_path = project_dir / "README.md"
    if readme_path.exists():
        rel = str(readme_path.relative_to(project_dir))
        files[rel] = readme_path.read_text(errors="ignore")

    return files


def _collect_previous_requests(project_id: str) -> list[str]:
    """Load previous modification requests from call summaries."""
    requests = []
    if SUMMARIES_DIR.exists():
        for summary_file in sorted(SUMMARIES_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(summary_file.read_text())
                if data.get("project") == project_id:
                    for req in data.get("modification_requests", []):
                        if req not in requests:
                            requests.append(req)
            except (json.JSONDecodeError, KeyError):
                continue
            if len(requests) >= 10:
                break
    return requests


def _truncate_content(files: dict[str, str], max_chars: int = _MAX_RAW_CHARS) -> str:
    """Combine file contents, truncating if needed.

    Priority (kept first):
    1. README.md, docs/
    2. openspec/specs/
    3. design-snapshot.md
    4. openspec/changes/ (newest first)
    """
    # Sort by priority
    priority_order = []
    for path, content in files.items():
        if path == "README.md":
            priority_order.append((0, path, content))
        elif path.startswith("docs/"):
            priority_order.append((1, path, content))
        elif "specs/" in path and path.endswith("spec.md"):
            priority_order.append((2, path, content))
        elif path == "design-snapshot.md":
            priority_order.append((3, path, content))
        elif "changes/" in path:
            priority_order.append((4, path, content))
        else:
            priority_order.append((5, path, content))

    priority_order.sort(key=lambda x: x[0])

    parts = []
    total = 0
    for _, path, content in priority_order:
        section = f"--- {path} ---\n{content}\n"
        if total + len(section) > max_chars:
            remaining = max_chars - total
            if remaining > 200:
                parts.append(section[:remaining] + "\n[...csonkolva]")
            break
        parts.append(section)
        total += len(section)

    return "\n".join(parts)


def _get_source_mtimes(project_dir: Path, files: dict[str, str]) -> dict[str, float]:
    """Get mtime for each source file."""
    mtimes = {}
    for rel_path in files:
        full_path = project_dir / rel_path
        if full_path.exists():
            mtimes[rel_path] = full_path.stat().st_mtime
    return mtimes


# --- Cache ---

def _cache_path(project_id: str) -> Path:
    return INDEXES_DIR / f"{project_id}.json"


def read_cache(project_id: str, project_dir: Path) -> dict | None:
    """Read cached index if fresh. Returns None if stale or missing."""
    cache_file = _cache_path(project_id)
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    # Check mtimes — only invalidate if existing files were modified
    # Missing files don't invalidate (project may have been cleaned/moved)
    cached_mtimes = data.get("source_files", {})
    for rel_path, cached_mtime in cached_mtimes.items():
        full_path = project_dir / rel_path
        if full_path.exists() and full_path.stat().st_mtime > cached_mtime:
            return None  # File modified

    # Also check for new files not in cache
    current_files = _collect_source_files(project_dir)
    new_files = set(current_files.keys()) - set(cached_mtimes.keys())
    if new_files:
        return None  # New files added since cache was built

    return data


def write_cache(project_id: str, summary: dict, source_mtimes: dict[str, float], model: str) -> Path:
    """Write index cache to disk."""
    INDEXES_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(project_id)

    cache_data = {
        "summary": summary,
        "generated_at": datetime.now().isoformat(),
        "source_files": source_mtimes,
        "model": model,
    }

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

    return cache_file


# --- Main indexer ---

async def generate_index(project_dir: str | Path, project_id: str) -> dict:
    """Generate a structured project index using Claude Haiku.

    Args:
        project_dir: Path to the customer's project directory.
        project_id: Project identifier for cache key.

    Returns:
        Summary dict with project_name, description, modules, design, status, previous_requests.
    """
    project_dir = Path(project_dir)

    # Check cache first
    cached = read_cache(project_id, project_dir)
    if cached:
        log.info("index_cache_hit", project=project_id)
        return cached["summary"]

    log.info("index_generating", project=project_id)

    # Collect source files
    files = _collect_source_files(project_dir)
    if not files:
        log.warning("index_no_files", project=project_id)
        return {}

    # Collect previous requests from call summaries
    previous_requests = _collect_previous_requests(project_id)

    # Build combined content
    combined = _truncate_content(files)

    # Add previous requests if any
    if previous_requests:
        combined += "\n\n--- Korábbi ügyfélkérések ---\n"
        combined += "\n".join(f"- {r}" for r in previous_requests)

    # Send to Claude Haiku
    model = "claude-haiku-4-5"
    client = AsyncAnthropic()
    response = await client.messages.create(
        model=model,
        system=_SUMMARY_PROMPT,
        messages=[{"role": "user", "content": combined}],
        max_tokens=1000,
    )

    # Parse response — strip markdown code fences if present
    raw_text = response.content[0].text if response.content else ""
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        # Remove ```json ... ``` wrapper
        lines = raw_text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_text = "\n".join(lines)
    try:
        summary = json.loads(raw_text)
    except (json.JSONDecodeError, IndexError):
        log.error("index_parse_error", raw=response.content[0].text[:200] if response.content else "")
        summary = {
            "project_name": project_id,
            "description": response.content[0].text if response.content else "",
            "modules": [],
            "design": {},
            "status": {"done": [], "in_progress": [], "planned": []},
            "previous_requests": previous_requests,
        }

    # Merge in previous requests (Haiku might not have them from call logs)
    if previous_requests and not summary.get("previous_requests"):
        summary["previous_requests"] = previous_requests

    # Cache
    source_mtimes = _get_source_mtimes(project_dir, files)
    cache_path = write_cache(project_id, summary, source_mtimes, model)
    log.info("index_generated", project=project_id, cache=str(cache_path))

    return summary


def format_summary_for_prompt(summary: dict) -> str:
    """Format the index summary as text for the voice agent system prompt."""
    if not summary:
        return ""

    parts = []

    if summary.get("project_name"):
        parts.append(f"Projekt: {summary['project_name']}")
    if summary.get("description"):
        parts.append(f"Leírás: {summary['description']}")

    modules = summary.get("modules", [])
    if modules:
        mod_lines = []
        for m in modules:
            if isinstance(m, dict):
                mod_lines.append(f"  - {m.get('name', '?')}: {m.get('description', '')}")
            else:
                mod_lines.append(f"  - {m}")
        parts.append("Modulok:\n" + "\n".join(mod_lines))

    design = summary.get("design", {})
    if design and isinstance(design, dict):
        design_parts = []
        if design.get("colors"):
            design_parts.append(f"Színek: {design['colors']}")
        if design.get("font"):
            design_parts.append(f"Font: {design['font']}")
        if design.get("style"):
            design_parts.append(f"Stílus: {design['style']}")
        if design_parts:
            parts.append("Design: " + ", ".join(design_parts))

    status = summary.get("status", {})
    if status and isinstance(status, dict):
        status_lines = []
        for label, key in [("Kész", "done"), ("Folyamatban", "in_progress"), ("Tervezett", "planned")]:
            items = status.get(key, [])
            if items:
                status_lines.append(f"  {label}: {', '.join(items)}")
        if status_lines:
            parts.append("Állapot:\n" + "\n".join(status_lines))

    prev = summary.get("previous_requests", [])
    if prev:
        parts.append("Korábbi ügyfélkérések:\n" + "\n".join(f"  - {r}" for r in prev))

    return "\n\n".join(parts)

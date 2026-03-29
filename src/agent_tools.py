"""Tools for the Deep Layer agent — read-only project investigation during live calls."""

import os
import re
import subprocess
from pathlib import Path

import structlog

from .i18n import _TOOL_DESCRIPTIONS, get_text

log = structlog.get_logger()

# Max chars returned by file_read
_MAX_FILE_CHARS = 2000
# Max lines returned by grep_search
_MAX_GREP_LINES = 30


def _tool_desc(key: str) -> str:
    """Get localized tool description."""
    return get_text(_TOOL_DESCRIPTIONS).get(key, key)


# --- Anthropic tool_use definitions ---

def get_tool_definitions() -> list[dict]:
    """Return tool definitions with localized descriptions."""
    return [
        {
            "name": "openspec_read",
            "description": _tool_desc("openspec_read"),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Spec or change name, e.g. 'navbar' or 'green-menu'",
                    }
                },
                "required": ["name"],
            },
        },
        {
            "name": "docs_read",
            "description": _tool_desc("docs_read"),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to docs/, e.g. 'design.md' or 'figma-export.md'. Leave empty to list available docs.",
                        "default": "",
                    }
                },
                "required": [],
            },
        },
        {
            "name": "design_check",
            "description": _tool_desc("design_check"),
            "input_schema": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Component name to look up, e.g. 'Navbar', 'Button'",
                    }
                },
                "required": ["component"],
            },
        },
        {
            "name": "file_read",
            "description": _tool_desc("file_read"),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path, e.g. 'src/components/Navbar.tsx'",
                    }
                },
                "required": ["path"],
            },
        },
        {
            "name": "grep_search",
            "description": _tool_desc("grep_search"),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Subdirectory to search in (relative), default is project root",
                        "default": ".",
                    },
                },
                "required": ["pattern"],
            },
        },
    ]


# Keep backward compat — callers import TOOL_DEFINITIONS
TOOL_DEFINITIONS = get_tool_definitions()


# --- Path sandboxing ---

def _safe_resolve(project_dir: Path, relative_path: str) -> Path:
    """Resolve a relative path safely within project_dir.

    Raises ValueError if the path escapes the sandbox.
    """
    # Reject absolute paths
    if os.path.isabs(relative_path):
        raise ValueError(f"Absolute paths not allowed: {relative_path}")

    # Reject obvious traversal
    if ".." in relative_path.split(os.sep):
        raise ValueError(f"Path traversal not allowed: {relative_path}")

    resolved = (project_dir / relative_path).resolve()

    # Final check: must be under project_dir
    project_resolved = project_dir.resolve()
    if not str(resolved).startswith(str(project_resolved) + os.sep) and resolved != project_resolved:
        raise ValueError(f"Path escapes sandbox: {relative_path}")

    # Reject symlinks that point outside
    if resolved.is_symlink():
        target = resolved.resolve()
        if not str(target).startswith(str(project_resolved) + os.sep):
            raise ValueError(f"Symlink escapes sandbox: {relative_path}")

    return resolved


# --- Tool implementations ---

def file_read(project_dir: Path, path: str) -> str:
    """Read a file, max _MAX_FILE_CHARS."""
    resolved = _safe_resolve(project_dir, path)
    if not resolved.exists():
        return f"File not found: {path}"
    if not resolved.is_file():
        return f"Not a file: {path}"
    try:
        content = resolved.read_text(errors="replace")
        if len(content) > _MAX_FILE_CHARS:
            return content[:_MAX_FILE_CHARS] + "\n[...csonkolva]"
        return content
    except Exception as e:
        return f"Error reading {path}: {e}"


def grep_search(project_dir: Path, pattern: str, path: str = ".") -> str:
    """Search for pattern using grep, return matching lines."""
    search_dir = _safe_resolve(project_dir, path)
    if not search_dir.exists():
        return f"Directory not found: {path}"
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.ts", "--include=*.tsx",
             "--include=*.js", "--include=*.jsx", "--include=*.md", "--include=*.yaml",
             "--include=*.yml", "--include=*.json", "--include=*.html", "--include=*.css",
             "-E", pattern, str(search_dir)],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_dir),
        )
        lines = result.stdout.strip().split("\n")
        # Make paths relative to project_dir
        relative_lines = []
        prefix = str(project_dir) + "/"
        for line in lines[:_MAX_GREP_LINES]:
            if line.startswith(prefix):
                line = line[len(prefix):]
            relative_lines.append(line)
        output = "\n".join(relative_lines)
        if len(lines) > _MAX_GREP_LINES:
            output += f"\n[...{len(lines) - _MAX_GREP_LINES} more results]"
        return output if output.strip() else "No matches found."
    except subprocess.TimeoutExpired:
        return "Search timed out (5s limit)."
    except Exception as e:
        return f"Search error: {e}"


def openspec_read(project_dir: Path, name: str) -> str:
    """Read a spec or change from the project's openspec directory."""
    # Try as spec first
    spec_path = project_dir / "openspec" / "specs" / name / "spec.md"
    if spec_path.exists():
        content = spec_path.read_text(errors="replace")
        if len(content) > _MAX_FILE_CHARS:
            return content[:_MAX_FILE_CHARS] + "\n[...csonkolva]"
        return content

    # Try as change
    change_dir = project_dir / "openspec" / "changes" / name
    if change_dir.exists():
        parts = []
        for fname in ["proposal.md", "design.md", "tasks.md"]:
            fpath = change_dir / fname
            if fpath.exists():
                parts.append(f"--- {fname} ---\n{fpath.read_text(errors='replace')}")
        content = "\n\n".join(parts) if parts else "Change directory exists but no artifacts found."
        if len(content) > _MAX_FILE_CHARS:
            return content[:_MAX_FILE_CHARS] + "\n[...csonkolva]"
        return content

    # List available specs and changes
    available = []
    specs_dir = project_dir / "openspec" / "specs"
    if specs_dir.exists():
        available.extend(f"spec: {d.name}" for d in specs_dir.iterdir() if d.is_dir())
    changes_dir = project_dir / "openspec" / "changes"
    if changes_dir.exists():
        available.extend(f"change: {d.name}" for d in changes_dir.iterdir() if d.is_dir())
    if available:
        return f"'{name}' not found. Available:\n" + "\n".join(available)
    return f"No openspec directory found in project."


def docs_read(project_dir: Path, path: str = "") -> str:
    """Read documentation from the project's docs/ directory."""
    docs_dir = project_dir / "docs"
    if not docs_dir.exists():
        return "No docs/ directory found in project."

    if not path:
        # List available docs
        files = []
        for f in sorted(docs_dir.rglob("*.md")):
            rel = f.relative_to(docs_dir)
            files.append(str(rel))
        if not files:
            return "docs/ directory exists but contains no .md files."
        return "Available docs:\n" + "\n".join(f"- {f}" for f in files)

    resolved = _safe_resolve(project_dir, f"docs/{path}")
    if not resolved.exists():
        return f"Doc not found: docs/{path}"
    try:
        content = resolved.read_text(errors="replace")
        if len(content) > _MAX_FILE_CHARS:
            return content[:_MAX_FILE_CHARS] + "\n[...csonkolva]"
        return content
    except Exception as e:
        return f"Error reading docs/{path}: {e}"


def design_check(project_dir: Path, component: str) -> str:
    """Extract component info from design-snapshot.md."""
    snapshot_path = project_dir / "design-snapshot.md"
    if not snapshot_path.exists():
        return "No design-snapshot.md found in project."
    content = snapshot_path.read_text(errors="replace")

    # Find the heading containing the component name, then capture everything until next heading
    heading_pattern = re.compile(
        r"^(#{{1,4}}\s+[^\n]*{comp}[^\n]*)\n".format(comp=re.escape(component)),
        re.IGNORECASE | re.MULTILINE,
    )
    heading_match = heading_pattern.search(content)
    if not heading_match:
        return f"Component '{component}' not found in design-snapshot.md."

    start = heading_match.start()
    # Find the next heading at the same or higher level
    next_heading = re.search(r"^#{1,4}\s+", content[heading_match.end():], re.MULTILINE)
    end = heading_match.end() + next_heading.start() if next_heading else len(content)
    section = content[start:end].strip()
    if len(section) > _MAX_FILE_CHARS:
        return section[:_MAX_FILE_CHARS] + "\n[...csonkolva]"
    return section


# --- Tool dispatcher ---

def execute_tool(tool_name: str, tool_input: dict, project_dir: Path) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if tool_name == "openspec_read":
            return openspec_read(project_dir, tool_input["name"])
        elif tool_name == "docs_read":
            return docs_read(project_dir, tool_input.get("path", ""))
        elif tool_name == "design_check":
            return design_check(project_dir, tool_input["component"])
        elif tool_name == "file_read":
            return file_read(project_dir, tool_input["path"])
        elif tool_name == "grep_search":
            return grep_search(project_dir, tool_input["pattern"], tool_input.get("path", "."))
        else:
            return f"Unknown tool: {tool_name}"
    except ValueError as e:
        # Sandbox violation
        log.warning("tool_sandbox_violation", tool=tool_name, error=str(e))
        return f"Access denied: {e}"
    except Exception as e:
        log.error("tool_execution_error", tool=tool_name, error=str(e))
        return f"Tool error: {e}"

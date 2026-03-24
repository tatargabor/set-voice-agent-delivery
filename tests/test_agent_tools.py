"""Tests for agent tools — sandboxing, file read, grep search."""

import os
from pathlib import Path
from src.agent_tools import (
    file_read, grep_search, openspec_read, design_check,
    execute_tool, _safe_resolve,
)
import pytest


@pytest.fixture
def project(tmp_path):
    """Create a sample project structure."""
    # Source files
    src = tmp_path / "src" / "components"
    src.mkdir(parents=True)
    (src / "Navbar.tsx").write_text("export default function Navbar() {\n  return <nav className='bg-blue-600'>Menu</nav>\n}")
    (src / "Footer.tsx").write_text("export default function Footer() {\n  return <footer>Footer</footer>\n}")

    # OpenSpec
    spec_dir = tmp_path / "openspec" / "specs" / "navbar"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("### Requirement: Navbar\nThe navbar SHALL be blue.")

    change_dir = tmp_path / "openspec" / "changes" / "green-menu"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("## Why\nCustomer wants green menu.")
    (change_dir / "tasks.md").write_text("- [ ] Change menu color")

    # Design snapshot
    (tmp_path / "design-snapshot.md").write_text(
        "# Design Tokens\n\n## Navbar\nBackground: #2563EB\nHeight: 64px\n\n## Button\nBorder-radius: 8px\n"
    )

    return tmp_path


# --- file_read ---

def test_file_read_returns_content(project):
    result = file_read(project, "src/components/Navbar.tsx")
    assert "bg-blue-600" in result


def test_file_read_not_found(project):
    result = file_read(project, "nonexistent.txt")
    assert "not found" in result.lower()


def test_file_read_truncates(project):
    (project / "big.txt").write_text("A" * 3000)
    result = file_read(project, "big.txt")
    assert len(result) <= 2100
    assert "csonkolva" in result


# --- grep_search ---

def test_grep_search_finds_matches(project):
    result = grep_search(project, "bg-blue")
    assert "Navbar.tsx" in result
    assert "bg-blue-600" in result


def test_grep_search_no_matches(project):
    result = grep_search(project, "nonexistent_pattern_xyz")
    assert "no matches" in result.lower()


def test_grep_search_subdirectory(project):
    result = grep_search(project, "Footer", "src/components")
    assert "Footer" in result


# --- openspec_read ---

def test_openspec_read_spec(project):
    result = openspec_read(project, "navbar")
    assert "SHALL be blue" in result


def test_openspec_read_change(project):
    result = openspec_read(project, "green-menu")
    assert "green menu" in result.lower()


def test_openspec_read_not_found(project):
    result = openspec_read(project, "nonexistent")
    assert "not found" in result.lower() or "available" in result.lower()


# --- design_check ---

def test_design_check_finds_component(project):
    result = design_check(project, "Navbar")
    assert "#2563EB" in result


def test_design_check_not_found(project):
    result = design_check(project, "Sidebar")
    assert "not found" in result.lower()


# --- Path sandboxing ---

def test_sandbox_rejects_absolute_path(project):
    with pytest.raises(ValueError, match="Absolute"):
        _safe_resolve(project, "/etc/passwd")


def test_sandbox_rejects_traversal(project):
    with pytest.raises(ValueError, match="traversal"):
        _safe_resolve(project, "../../etc/passwd")


def test_sandbox_rejects_sneaky_traversal(project):
    with pytest.raises(ValueError, match="traversal"):
        _safe_resolve(project, "src/../../etc/passwd")


def test_sandbox_allows_valid_path(project):
    resolved = _safe_resolve(project, "src/components/Navbar.tsx")
    assert resolved.exists()


# --- execute_tool dispatcher ---

def test_execute_tool_dispatches(project):
    result = execute_tool("file_read", {"path": "src/components/Navbar.tsx"}, project)
    assert "bg-blue-600" in result


def test_execute_tool_sandbox_violation(project):
    result = execute_tool("file_read", {"path": "/etc/passwd"}, project)
    assert "denied" in result.lower()


def test_execute_tool_unknown(project):
    result = execute_tool("unknown_tool", {}, project)
    assert "unknown" in result.lower()

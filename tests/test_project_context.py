"""Tests for project context loader."""

from pathlib import Path
from src.project_context import load_project_context, ProjectContext


def test_load_from_test_dir(tmp_path):
    """Load context from a directory with sample files."""
    # Create sample project structure
    (tmp_path / "README.md").write_text("# Test Project\nThis is a web builder project.")
    specs_dir = tmp_path / "openspec" / "specs" / "navbar"
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.md").write_text("### Requirement: Navbar color\nThe navbar SHALL be blue.")

    changes_dir = tmp_path / "openspec" / "changes" / "green-menu"
    changes_dir.mkdir(parents=True)
    (changes_dir / ".openspec.yaml").write_text("schema: spec-driven")
    (changes_dir / "proposal.md").write_text("## Why\nCustomer wants green menu.")

    ctx = load_project_context(tmp_path)
    assert "Test Project" in ctx.project_summary
    assert "navbar" in ctx.specs_summary.lower()
    assert "green-menu" in ctx.active_changes


def test_truncation(tmp_path):
    """Context should be truncated at 4000 chars."""
    (tmp_path / "README.md").write_text("A" * 5000)
    ctx = load_project_context(tmp_path)
    prompt = ctx.to_prompt_section()
    assert len(prompt) <= 4100  # 4000 + "[...csonkolva]"


def test_missing_dir():
    """Missing project dir returns empty context."""
    ctx = load_project_context("/nonexistent/path")
    assert ctx.project_summary == ""
    assert ctx.to_prompt_section() == ""


def test_previous_call_log(tmp_path):
    """Load previous call for customer."""
    import json
    logs_dir = tmp_path / "logs"
    day_dir = logs_dir / "2026-03-24"
    day_dir.mkdir(parents=True)
    (day_dir / "20260324_120000_gbor.json").write_text(json.dumps({
        "timestamp_start": "2026-03-24T12:00:00",
        "transcript": [
            {"role": "agent", "text": "Szia Gábor!"},
            {"role": "customer", "text": "Szia!"},
        ]
    }))

    ctx = load_project_context(tmp_path, customer_name="Gábor", call_logs_dir=logs_dir)
    assert ctx.previous_call is not None
    assert "Gábor" in ctx.previous_call

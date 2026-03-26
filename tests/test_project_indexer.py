"""Tests for project indexer — index generation, cache, and API endpoint."""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.project_indexer import (
    _collect_source_files,
    _truncate_content,
    _collect_previous_requests,
    read_cache,
    write_cache,
    format_summary_for_prompt,
    generate_index,
)


@pytest.fixture
def mock_project(tmp_path):
    """Create a mock project directory with docs and openspec."""
    # README
    (tmp_path / "README.md").write_text("# Test Project\nA test web project.")

    # docs/
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "design.md").write_text("## Design\nColors: blue #2563EB\nFont: Inter")
    (docs / "api.md").write_text("## API\nREST endpoints for user management.")

    # openspec/specs/
    specs = tmp_path / "openspec" / "specs" / "user-auth"
    specs.mkdir(parents=True)
    (specs / "spec.md").write_text("### Requirement: User login\nUsers SHALL authenticate via email.")

    # openspec/changes/
    changes = tmp_path / "openspec" / "changes" / "add-dashboard"
    changes.mkdir(parents=True)
    (changes / ".openspec.yaml").write_text("schema: spec-driven")
    (changes / "proposal.md").write_text("## Why\nNeed a dashboard for metrics.")
    (changes / "tasks.md").write_text("- [x] 1.1 Create component\n- [ ] 1.2 Add charts")

    return tmp_path


class TestCollectSourceFiles:
    def test_collects_all_file_types(self, mock_project):
        files = _collect_source_files(mock_project)
        assert "README.md" in files
        assert "docs/design.md" in files
        assert "docs/api.md" in files
        assert "openspec/specs/user-auth/spec.md" in files
        assert "openspec/changes/add-dashboard/proposal.md" in files
        assert "openspec/changes/add-dashboard/tasks.md" in files

    def test_empty_project(self, tmp_path):
        files = _collect_source_files(tmp_path)
        assert len(files) == 0


class TestTruncateContent:
    def test_all_content_fits(self, mock_project):
        files = _collect_source_files(mock_project)
        result = _truncate_content(files, max_chars=50000)
        assert "README.md" in result
        assert "docs/design.md" in result

    def test_truncation_keeps_priority(self, mock_project):
        files = _collect_source_files(mock_project)
        # Very small limit — should keep README first
        result = _truncate_content(files, max_chars=100)
        assert "README.md" in result


class TestCache:
    def test_write_and_read(self, tmp_path, mock_project):
        summary = {"project_name": "test", "description": "Test project"}
        mtimes = {"README.md": mock_project.joinpath("README.md").stat().st_mtime}

        with patch("src.project_indexer.INDEXES_DIR", tmp_path):
            write_cache("test-proj", summary, mtimes, "claude-haiku-4-5")
            result = read_cache("test-proj", mock_project)
            assert result is not None
            assert result["summary"]["project_name"] == "test"

    def test_cache_miss(self, tmp_path, mock_project):
        with patch("src.project_indexer.INDEXES_DIR", tmp_path):
            result = read_cache("nonexistent", mock_project)
            assert result is None

    def test_cache_stale_after_file_change(self, tmp_path, mock_project):
        summary = {"project_name": "test"}
        mtimes = {"README.md": mock_project.joinpath("README.md").stat().st_mtime - 100}

        with patch("src.project_indexer.INDEXES_DIR", tmp_path):
            write_cache("test-proj", summary, mtimes, "claude-haiku-4-5")
            # File is newer than cached mtime → stale
            result = read_cache("test-proj", mock_project)
            assert result is None


class TestFormatSummary:
    def test_full_summary(self):
        summary = {
            "project_name": "MicroWeb",
            "description": "Egyoldalas weboldal",
            "modules": [{"name": "Főoldal", "description": "Hero section + CTA"}],
            "design": {"colors": "kék #2563EB", "font": "Inter", "style": "modern"},
            "status": {"done": ["Főoldal"], "in_progress": ["Blog"], "planned": ["SEO"]},
            "previous_requests": ["Logó zöldre"],
        }
        result = format_summary_for_prompt(summary)
        assert "MicroWeb" in result
        assert "Főoldal" in result
        assert "kék" in result
        assert "Logó zöldre" in result

    def test_empty_summary(self):
        assert format_summary_for_prompt({}) == ""


@pytest.mark.conversation
class TestGenerateIndex:
    @pytest.mark.asyncio
    async def test_generate_with_mock_claude(self, mock_project, tmp_path):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "project_name": "Test Project",
            "description": "A test web project",
            "modules": [],
            "design": {},
            "status": {"done": [], "in_progress": [], "planned": []},
            "previous_requests": [],
        }))]

        with patch("src.project_indexer.INDEXES_DIR", tmp_path), \
             patch("src.project_indexer.AsyncAnthropic") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_index(mock_project, "test-project")
            assert result["project_name"] == "Test Project"

            # Verify cache was written
            cache_file = tmp_path / "test-project.json"
            assert cache_file.exists()

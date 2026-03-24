"""Tests for agent cache, research mode routing, and config."""

from pathlib import Path
from src.agent_cache import AgentCache, get_or_create_cache, _cache
from src.response_layers import _is_research_question
from src.config import AppSettings, load_app_settings, reset_settings, get_settings
import pytest


@pytest.fixture
def project(tmp_path):
    """Create a sample project with specs and changes."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "README.md").write_text("# My Project")

    spec_dir = tmp_path / "openspec" / "specs" / "auth"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("### Requirement: Login\nUsers SHALL log in.")

    change_dir = tmp_path / "openspec" / "changes" / "add-dark-mode"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("## Why\nUsers want dark mode.")
    (change_dir / "tasks.md").write_text("- [x] Task 1\n- [ ] Task 2\n- [ ] Task 3")

    return tmp_path


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear agent cache between tests."""
    _cache.clear()
    yield
    _cache.clear()


# --- AgentCache ---

def test_cache_populates_file_index(project):
    cache = get_or_create_cache(project)
    assert "src/main.py" in cache.file_index
    assert "README.md" in cache.file_index


def test_cache_populates_spec_summaries(project):
    cache = get_or_create_cache(project)
    assert "auth" in cache.spec_summaries
    assert "Login" in cache.spec_summaries["auth"]


def test_cache_populates_change_summaries(project):
    cache = get_or_create_cache(project)
    assert "add-dark-mode" in cache.change_summaries
    assert "1/3" in cache.change_summaries["add-dark-mode"]


def test_cache_returns_same_on_second_call(project):
    cache1 = get_or_create_cache(project)
    cache2 = get_or_create_cache(project)
    assert cache1 is cache2


def test_cache_add_finding(project):
    cache = get_or_create_cache(project)
    cache.add_finding("The navbar is blue")
    assert "The navbar is blue" in cache.findings
    # Dedup
    cache.add_finding("The navbar is blue")
    assert cache.findings.count("The navbar is blue") == 1


def test_cache_to_context_string(project):
    cache = get_or_create_cache(project)
    ctx = cache.to_context_string()
    assert "src/main.py" in ctx
    assert "auth" in ctx
    assert "add-dark-mode" in ctx


# --- _is_research_question ---

def test_research_question_detects_keywords():
    assert _is_research_question("Mi van a spec-ben?")
    assert _is_research_question("Keress rá a navbar-ra")
    assert _is_research_question("Nézd meg a fájlt")
    assert _is_research_question("Hogyan van implementálva a login?")
    assert _is_research_question("Melyik fájl tartalmazza?")


def test_research_question_rejects_simple():
    assert not _is_research_question("Igen")
    assert not _is_research_question("Köszönöm szépen")
    assert not _is_research_question("Mikor lesz kész?")


# --- Config defaults ---

def test_config_defaults():
    reset_settings()
    settings = load_app_settings(Path("/nonexistent/config.yaml"))
    assert settings.research.mode == "tool_use"
    assert settings.models.fast == "claude-haiku-4-5"
    assert settings.voice.max_sentences == 3
    reset_settings()

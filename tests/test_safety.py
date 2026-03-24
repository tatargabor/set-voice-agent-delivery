"""Tests for call safety checks."""

import datetime
import pytest
from pathlib import Path
from src.safety import CallSafety


@pytest.fixture
def safety(tmp_path):
    """Create CallSafety with a temporary DNC file."""
    dnc_file = tmp_path / "dnc.txt"
    return CallSafety(dnc_path=dnc_file)


def test_dnc_blocks_listed_number(safety):
    safety._dnc_path.write_text("+36301234567\n+36309876543\n")
    assert safety.check_dnc("+36301234567") is True


def test_dnc_allows_unlisted_number(safety):
    safety._dnc_path.write_text("+36301234567\n")
    assert safety.check_dnc("+36309999999") is False


def test_dnc_empty_file(safety):
    assert safety.check_dnc("+36301234567") is False


def test_add_to_dnc(safety):
    safety.add_to_dnc("+36301234567")
    assert "+36301234567" in safety._dnc_path.read_text()
    assert safety.check_dnc("+36301234567") is True


def test_legal_hours_blocked_early():
    safety = CallSafety()
    early = datetime.datetime(2026, 3, 24, 6, 30)
    assert safety.check_legal_hours(now=early) is True


def test_legal_hours_blocked_late():
    safety = CallSafety()
    late = datetime.datetime(2026, 3, 24, 21, 0)
    assert safety.check_legal_hours(now=late) is True


def test_legal_hours_allowed():
    safety = CallSafety()
    afternoon = datetime.datetime(2026, 3, 24, 14, 0)
    assert safety.check_legal_hours(now=afternoon) is False


def test_pre_call_check_passes(safety):
    """No DNC, within hours → should not raise."""
    noon = datetime.datetime(2026, 3, 24, 12, 0)
    # Monkey-patch check_legal_hours to use fixed time
    safety.check_legal_hours = lambda now=None: False
    safety.pre_call_check("+36301234567")


def test_pre_call_check_dnc_fails(safety):
    safety.add_to_dnc("+36301234567")
    safety.check_legal_hours = lambda now=None: False
    with pytest.raises(ValueError, match="Do Not Call"):
        safety.pre_call_check("+36301234567")

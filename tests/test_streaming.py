"""Tests for streaming response features."""

from src.agent import is_sentence_boundary


def test_sentence_boundary_period():
    assert is_sentence_boundary("Szia Gábor.") is True


def test_sentence_boundary_exclamation():
    assert is_sentence_boundary("Nagyszerű!") is True


def test_sentence_boundary_question():
    assert is_sentence_boundary("Megkaptad?") is True


def test_sentence_boundary_long_comma():
    text = "Rendben, feljegyzem a kéréseket és továbbítom a csapatnak, akik majd foglalkoznak vele és visszajeleznek,"
    assert len(text) > 80
    assert is_sentence_boundary(text) is True


def test_no_boundary_short_comma():
    assert is_sentence_boundary("Igen,") is False


def test_no_boundary_mid_word():
    assert is_sentence_boundary("Szuper") is False


def test_no_boundary_empty():
    assert is_sentence_boundary("") is False
    assert is_sentence_boundary("   ") is False

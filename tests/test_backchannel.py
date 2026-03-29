"""Tests for backchannel filter."""

import pytest
from src.pipeline import is_backchannel, is_stop_word, _normalize


@pytest.fixture(autouse=True)
def _set_hungarian(monkeypatch):
    """These tests use Hungarian word lists — force language to hu."""
    from src import config
    settings = config.get_settings()
    monkeypatch.setattr(settings, "language", "hu")


class TestNormalize:
    def test_lowercase_strip(self):
        assert _normalize("  Igen  ") == "igen"

    def test_remove_punctuation(self):
        assert _normalize("Igen.") == "igen"
        assert _normalize("Oké!") == "oké"
        assert _normalize("Nem?") == "nem"


class TestIsBackchannel:
    def test_single_backchannel_words(self):
        for word in ["mhm", "aha", "igen", "ja", "jó", "oké", "értem", "rendben", "persze"]:
            assert is_backchannel(word), f"{word} should be backchannel"

    def test_with_punctuation(self):
        assert is_backchannel("Igen.")
        assert is_backchannel("Oké!")
        assert is_backchannel("Aha,")

    def test_with_casing(self):
        assert is_backchannel("IGEN")
        assert is_backchannel("Rendben")

    def test_two_word_backchannel(self):
        assert is_backchannel("igen igen")
        assert is_backchannel("ja ja")

    def test_not_backchannel_three_words(self):
        assert not is_backchannel("igen igen igen")

    def test_not_backchannel_unknown(self):
        assert not is_backchannel("kosárrendszer")

    def test_stop_words_not_backchannel(self):
        assert not is_backchannel("nem")
        assert not is_backchannel("stop")
        assert not is_backchannel("várj")


class TestIsStopWord:
    def test_stop_words(self):
        for word in ["nem", "stop", "várj", "de", "figyelj", "halló"]:
            assert is_stop_word(word), f"{word} should be stop word"

    def test_stop_with_punctuation(self):
        assert is_stop_word("Nem!")
        assert is_stop_word("Várj.")

    def test_stop_in_phrase(self):
        assert is_stop_word("de várj")

    def test_backchannel_not_stop(self):
        assert not is_stop_word("igen")
        assert not is_stop_word("mhm")
        assert not is_stop_word("oké")

    def test_unknown_not_stop(self):
        assert not is_stop_word("kosárrendszer")

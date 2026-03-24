"""Tests for dual-layer response."""

from src.response_layers import _is_simple


def test_simple_greeting():
    assert _is_simple("Szia") is True
    assert _is_simple("Igen") is True
    assert _is_simple("Nem") is True
    assert _is_simple("Ok") is True
    assert _is_simple("Köszönöm") is True


def test_simple_short():
    assert _is_simple("Meg.") is True
    assert _is_simple("Halló?") is True


def test_not_simple_long():
    assert _is_simple("Szeretném, hogyha zöld lenne a menü a weboldalon.") is False


def test_not_simple_question():
    assert _is_simple("Mi a helyzet a weboldallal kapcsolatban?") is False

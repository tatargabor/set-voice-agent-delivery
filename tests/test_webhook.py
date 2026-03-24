"""Tests for Twilio webhook server."""

import pytest
from fastapi.testclient import TestClient
from src.webhook import app, configure, enable_inbound_mode


def test_twiml_response():
    """POST /twilio/voice should return valid TwiML with Stream element."""
    client = TestClient(app)
    response = client.post("/twilio/voice", headers={"host": "example.com"})
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    body = response.text
    assert "<Response>" in body
    assert "<Connect>" in body
    assert "<Stream" in body
    assert "wss://example.com/twilio/media-stream" in body


def test_inbound_twiml_with_caller():
    """Inbound call should return TwiML with Media Stream."""
    enable_inbound_mode()
    client = TestClient(app)
    response = client.post(
        "/twilio/voice",
        data={"From": "+36301234567", "CallSid": "CA_test_123"},
        headers={"host": "example.com"},
    )
    assert response.status_code == 200
    body = response.text
    assert "<Connect>" in body
    assert "<Stream" in body

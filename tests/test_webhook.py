"""Tests for Twilio webhook server."""

import pytest
from fastapi.testclient import TestClient
from src.webhook import app, configure


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

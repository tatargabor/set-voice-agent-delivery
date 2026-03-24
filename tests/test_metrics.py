"""Tests for call metrics and cost calculation."""

from datetime import datetime
from src.metrics import CallMetrics, mask_phone, calculate_costs


def test_mask_phone():
    assert mask_phone("+36203911669") == "+3620***1669"
    assert mask_phone("+1555123456") == "+1555***3456"
    assert mask_phone("short") == "***"


def test_calculate_costs():
    m = CallMetrics(
        call_id="CA123", timestamp_start=datetime.now(),
        customer_name="Test", script_name="test", phone_masked="+36***",
    )
    m.claude_input_tokens = 1000
    m.claude_output_tokens = 200
    m.tts_chars = 500
    m.stt_audio_ms = 60000  # 1 minute
    m.twilio_price = -0.063

    costs = calculate_costs(m)
    assert costs["twilio"] == 0.063
    assert costs["claude"] == (1000 * 3 + 200 * 15) / 1_000_000  # 0.006
    assert costs["google_tts"] == 500 * 4 / 1_000_000  # 0.000002
    assert abs(costs["soniox_stt"] - 0.002) < 0.0001  # 1 min × $0.002
    assert costs["total"] > 0


def test_add_claude_usage():
    m = CallMetrics(
        call_id="CA123", timestamp_start=datetime.now(),
        customer_name="Test", script_name="test", phone_masked="+36***",
    )
    m.add_claude_usage(100, 50)
    m.add_claude_usage(200, 80)
    assert m.claude_input_tokens == 300
    assert m.claude_output_tokens == 130
    assert m.claude_requests == 2


def test_add_error():
    m = CallMetrics(
        call_id="CA123", timestamp_start=datetime.now(),
        customer_name="Test", script_name="test", phone_masked="+36***",
    )
    m.add_error("stt_error", "Connection dropped")
    assert len(m.errors) == 1
    assert m.errors[0]["type"] == "stt_error"

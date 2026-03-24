"""Tests for call logger."""

import json
from datetime import datetime
from src.logger import CallLogger
from src.metrics import CallMetrics


def test_save_creates_json_file(tmp_path):
    metrics = CallMetrics(
        call_id="CA1234567890abcdef",
        timestamp_start=datetime(2026, 3, 24, 8, 38),
        customer_name="Gábor",
        script_name="website_followup",
        phone_masked="+3620***1669",
    )
    metrics.claude_input_tokens = 500
    metrics.claude_output_tokens = 100
    metrics.tts_chars = 200
    metrics.stt_audio_ms = 30000
    metrics.twilio_price = -0.063
    metrics.twilio_duration_sec = 54
    metrics.turn_count = 4
    metrics.response_times_ms = [1500, 2000, 1800, 1600]

    transcript = [
        {"role": "assistant", "content": "Szia Gábor!"},
        {"role": "user", "content": "Helló."},
    ]

    logger = CallLogger(logs_dir=tmp_path)
    filepath = logger.save(metrics, transcript, outcome="completed")

    assert filepath.exists()
    assert filepath.suffix == ".json"
    assert "2026-03-24" in str(filepath.parent.name)

    data = json.loads(filepath.read_text())
    assert data["call_id"] == "CA1234567890abcdef"
    assert data["outcome"] == "completed"
    assert data["phone_masked"] == "+3620***1669"
    assert data["duration_sec"] == 54
    assert data["cost"]["twilio"] == 0.063
    assert data["cost"]["total"] > 0
    assert len(data["transcript"]) == 2
    assert data["transcript"][0]["role"] == "agent"
    assert data["performance"]["turn_count"] == 4
    assert data["performance"]["avg_response_time_ms"] == 1725

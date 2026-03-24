"""Call logger — writes JSON log files per call."""

import json
import re
from datetime import datetime
from pathlib import Path

from .metrics import CallMetrics, calculate_costs

LOGS_DIR = Path(__file__).parent.parent / "logs" / "calls"


class CallLogger:
    """Write structured JSON log per completed call."""

    def __init__(self, logs_dir: Path = LOGS_DIR):
        self._logs_dir = logs_dir

    def save(
        self,
        metrics: CallMetrics,
        transcript: list[dict],
        outcome: str = "completed",
    ) -> Path:
        """Save call log to JSON file.

        Args:
            metrics: Collected call metrics.
            transcript: List of {"role": ..., "content": ...} dicts.
            outcome: One of "completed", "dropped", "error", "dnc".

        Returns:
            Path to the written JSON file.
        """
        metrics.timestamp_end = datetime.now()

        duration_sec = 0
        if metrics.twilio_duration_sec:
            duration_sec = metrics.twilio_duration_sec
        elif metrics.timestamp_end and metrics.timestamp_start:
            duration_sec = int((metrics.timestamp_end - metrics.timestamp_start).total_seconds())

        costs = calculate_costs(metrics)

        avg_response_ms = 0
        if metrics.response_times_ms:
            avg_response_ms = int(sum(metrics.response_times_ms) / len(metrics.response_times_ms))

        log_data = {
            "call_id": metrics.call_id,
            "timestamp_start": metrics.timestamp_start.isoformat(),
            "timestamp_end": metrics.timestamp_end.isoformat(),
            "duration_sec": duration_sec,
            "phone_masked": metrics.phone_masked,
            "customer_name": metrics.customer_name,
            "script": metrics.script_name,
            "outcome": outcome,
            "transcript": [
                {"role": "agent" if m["role"] == "assistant" else "customer", "text": m["content"]}
                for m in transcript
            ],
            "cost": costs,
            "performance": {
                "avg_response_time_ms": avg_response_ms,
                "response_times_ms": metrics.response_times_ms,
                "stt_audio_ms": metrics.stt_audio_ms,
                "tts_chars": metrics.tts_chars,
                "claude_input_tokens": metrics.claude_input_tokens,
                "claude_output_tokens": metrics.claude_output_tokens,
                "claude_requests": metrics.claude_requests,
                "barge_in_count": metrics.barge_in_count,
                "turn_count": metrics.turn_count,
            },
            "errors": metrics.errors,
        }

        # Write to file
        date_str = metrics.timestamp_start.strftime("%Y-%m-%d")
        time_str = metrics.timestamp_start.strftime("%H-%M")
        name_slug = re.sub(r"[^a-z0-9]", "", metrics.customer_name.lower())[:20]
        sid_short = metrics.call_id[:10] if len(metrics.call_id) > 10 else metrics.call_id

        day_dir = self._logs_dir / date_str
        day_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{sid_short}_{name_slug}_{time_str}.json"
        filepath = day_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return filepath

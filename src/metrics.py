"""Call metrics collection and cost calculation."""

import time
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CallMetrics:
    """Accumulates metrics during a call."""
    call_id: str
    timestamp_start: datetime
    customer_name: str
    script_name: str
    phone_masked: str

    timestamp_end: datetime | None = None

    # Claude usage
    claude_input_tokens: int = 0
    claude_output_tokens: int = 0
    claude_requests: int = 0

    # Google TTS
    tts_chars: int = 0

    # Soniox STT
    stt_audio_ms: int = 0

    # Twilio (fetched post-call)
    twilio_price: float | None = None
    twilio_duration_sec: int | None = None

    # Performance
    response_times_ms: list[int] = field(default_factory=list)
    barge_in_count: int = 0
    turn_count: int = 0

    # Tool calls
    tool_calls: list[dict] = field(default_factory=list)

    # Errors
    errors: list[dict] = field(default_factory=list)

    def add_claude_usage(self, input_tokens: int, output_tokens: int) -> None:
        self.claude_input_tokens += input_tokens
        self.claude_output_tokens += output_tokens
        self.claude_requests += 1

    def add_tool_calls(self, calls: list[dict]) -> None:
        self.tool_calls.extend(calls)

    def add_error(self, error_type: str, message: str) -> None:
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": message,
        })


def mask_phone(phone: str) -> str:
    """Mask a phone number for PII protection.

    +36203911669 → +3620***1669
    Keep country code + first 2 subscriber digits + last 4.
    """
    if len(phone) < 8:
        return "***"
    return phone[:5] + "***" + phone[-4:]


def calculate_costs(metrics: CallMetrics) -> dict[str, float]:
    """Calculate per-provider costs from collected metrics."""
    twilio = abs(metrics.twilio_price) if metrics.twilio_price else 0.0
    claude = (metrics.claude_input_tokens * 3 + metrics.claude_output_tokens * 15) / 1_000_000
    google_tts = metrics.tts_chars * 4 / 1_000_000
    soniox_stt = (metrics.stt_audio_ms / 1000 / 60) * 0.002

    total = twilio + claude + google_tts + soniox_stt
    return {
        "twilio": round(twilio, 6),
        "claude": round(claude, 6),
        "google_tts": round(google_tts, 6),
        "soniox_stt": round(soniox_stt, 6),
        "total": round(total, 6),
    }

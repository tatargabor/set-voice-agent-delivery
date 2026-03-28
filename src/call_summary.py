"""Post-call summary generator — extracts action items for the dev team."""

import json
from datetime import datetime
from pathlib import Path
from anthropic import AsyncAnthropic
import structlog

log = structlog.get_logger()

SUMMARIES_DIR = Path(__file__).parent.parent / "logs" / "summaries"


async def generate_call_summary(
    transcript: list[dict],
    customer_name: str,
    project_id: str,
    call_id: str,
) -> dict:
    """Generate a structured summary from the call transcript.

    Uses Claude to extract:
    - Modification/fix requests
    - Questions asked
    - Overall sentiment

    Returns dict with summary data and saves to logs/summaries/.
    """
    if not transcript:
        return {}

    from .i18n import _SUMMARY_PROMPT, _ROLE_LABELS, get_text

    # Format transcript for Claude
    role_labels = get_text(_ROLE_LABELS)
    lines = []
    for msg in transcript:
        role = role_labels["agent"] if msg["role"] == "assistant" else role_labels["customer"]
        lines.append(f"{role}: {msg['content']}")
    transcript_text = "\n".join(lines)

    client = AsyncAnthropic()
    response = await client.messages.create(
        model="claude-haiku-4-5",
        system=get_text(_SUMMARY_PROMPT),
        messages=[{"role": "user", "content": transcript_text}],
        max_tokens=500,
    )

    # Parse Claude's response
    try:
        summary_data = json.loads(response.content[0].text)
    except (json.JSONDecodeError, IndexError):
        summary_data = {
            "modification_requests": [],
            "questions": [],
            "sentiment": "semleges",
            "summary": response.content[0].text if response.content else "",
            "priority": "közepes",
        }

    # Enrich with call metadata
    summary_data["call_id"] = call_id
    summary_data["customer_name"] = customer_name
    summary_data["project"] = project_id
    summary_data["timestamp"] = datetime.now().isoformat()

    # Save to file
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_slug = "".join(c for c in customer_name.lower() if c.isalnum())[:20] or "anonymous"
    filename = f"{date_str}_{name_slug}.json"
    filepath = SUMMARIES_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    log.info("call_summary_saved", path=str(filepath),
             requests=len(summary_data.get("modification_requests", [])))

    return summary_data

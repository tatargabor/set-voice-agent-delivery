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

    # Format transcript for Claude
    lines = []
    for msg in transcript:
        role = "Agent" if msg["role"] == "assistant" else "Ügyfél"
        lines.append(f"{role}: {msg['content']}")
    transcript_text = "\n".join(lines)

    client = AsyncAnthropic()
    response = await client.messages.create(
        model="claude-haiku-4-5",
        system=(
            "Egy telefonhívás átiratát kapod. Az ügyfél a projektjéről beszélt a fejlesztő céggel. "
            "Készíts rövid, strukturált összefoglalót a fejlesztő csapat számára. "
            "Válaszolj JSON formátumban, az alábbi mezőkkel:\n"
            '- "modification_requests": lista a módosítási/javítási kérésekről (string lista)\n'
            '- "questions": lista a feltett kérdésekről amiket meg kell válaszolni (string lista)\n'
            '- "sentiment": az ügyfél hangulata: "elégedett", "semleges", "elégedetlen"\n'
            '- "summary": 1-2 mondatos összefoglaló a hívásról\n'
            '- "priority": "alacsony", "közepes", "magas" (ha sürgős kérés volt)\n'
            "Ha nincs módosítási kérés vagy kérdés, adj üres listát. Csak JSON-t adj vissza, semmi mást."
        ),
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

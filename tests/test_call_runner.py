"""Level 2 smoke tests for call runner wiring."""

import pytest
from src.script_loader import load_script
from src.safety import CallSafety
from src.agent import ConversationAgent


@pytest.mark.telephony
async def test_full_wiring_smoke():
    """Verify all components can be instantiated and wired together."""
    # Load script
    ctx = load_script("website_followup", {
        "customer_name": "Teszt Elek",
        "company_name": "WebBuilder Kft.",
        "website_url": "https://teszt.hu",
    })
    assert ctx.customer_name == "Teszt Elek"

    # Safety checks (should pass — not on DNC, within hours likely)
    safety = CallSafety()
    assert safety.check_dnc("+36301111111") is False

    # Agent can be created
    agent = ConversationAgent()
    assert agent.model == "claude-sonnet-4-6"

"""Level 0 tests: conversation flow with real Claude, no audio."""

import pytest
from src.agent import ConversationAgent, CallContext


@pytest.fixture
def agent():
    return ConversationAgent()


@pytest.fixture
def call_context():
    return CallContext(
        customer_name="Teszt Elek",
        company_name="WebBuilder Kft.",
        purpose="Megkérdezni megkapta-e a levelet a weboldaláról",
        website_url="https://teszt-elek.hu",
    )


@pytest.mark.conversation
async def test_greeting_is_hungarian(agent, call_context):
    """Agent greeting should be in Hungarian."""
    greeting, usage = await agent.get_greeting(call_context)
    assert len(greeting) > 10
    assert len(greeting) < 500
    assert usage["input_tokens"] > 0
    assert usage["output_tokens"] > 0


@pytest.mark.conversation
async def test_responds_to_yes(agent, call_context):
    """Agent should continue conversation when customer confirms."""
    await agent.get_greeting(call_context)
    response, _ = await agent.respond(call_context, "Igen, megkaptam a levelet.")
    assert len(response) > 5


@pytest.mark.conversation
async def test_responds_to_question(agent, call_context):
    """Agent should handle customer questions."""
    await agent.get_greeting(call_context)
    response, _ = await agent.respond(call_context, "Nem értem, mi az a weboldal?")
    assert len(response) > 5


@pytest.mark.conversation
async def test_handles_dnc_request(agent, call_context):
    """Agent should handle 'do not call' request gracefully."""
    await agent.get_greeting(call_context)
    response, _ = await agent.respond(call_context, "Ne hívjatok többet, kérem.")
    assert len(response) > 5

"""Claude-powered conversation agent for voice calls."""

import asyncio
from anthropic import AsyncAnthropic
from pydantic import BaseModel


class CallContext(BaseModel):
    """Context for a single call."""
    customer_name: str
    company_name: str
    purpose: str
    website_url: str | None = None
    history: list[dict] = []


class ConversationAgent:
    """Claude-based conversation engine for voice calls."""

    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.client = AsyncAnthropic()
        self.model = model

    def _build_system_prompt(self, ctx: CallContext) -> str:
        return f"""Te egy ügyfélszolgálati agent vagy a {ctx.company_name} nevében.

Kontextus:
- Ügyfél neve: {ctx.customer_name}
- Cél: {ctx.purpose}
{f'- Weboldal: {ctx.website_url}' if ctx.website_url else ''}

Szabályok:
- Rövid, természetes válaszok (1-2 mondat max)
- Magyarul beszélj, természetesen, közvetlenül
- Ha az ügyfél kér valamit, rögzítsd a record_request tool-lal
- Ha az ügyfél búcsúzik vagy lezárja, zárd le udvariasan
- Ne ismételd magad, ne légy túl formális"""

    async def get_greeting(self, ctx: CallContext) -> str:
        """Generate the opening greeting."""
        response = await self.client.messages.create(
            model=self.model,
            system=self._build_system_prompt(ctx),
            messages=[{"role": "user", "content": "(Az ügyfél felvette a telefont. Köszöntsd és térj a tárgyra.)"}],
            max_tokens=150,
        )
        text = response.content[0].text
        ctx.history.append({"role": "assistant", "content": text})
        return text

    async def respond(self, ctx: CallContext, customer_text: str) -> str:
        """Generate response to customer speech."""
        ctx.history.append({"role": "user", "content": customer_text})

        response = await self.client.messages.create(
            model=self.model,
            system=self._build_system_prompt(ctx),
            messages=ctx.history,
            max_tokens=150,
        )
        text = response.content[0].text
        ctx.history.append({"role": "assistant", "content": text})
        return text

    def should_hangup(self, agent_text: str) -> bool:
        """Check if the agent's response signals end of call."""
        endings = ["viszlát", "szép napot", "köszönöm a hívást", "további szép napot"]
        return any(w in agent_text.lower() for w in endings)

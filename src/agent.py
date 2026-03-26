"""Claude-powered conversation agent for voice calls."""

import asyncio
from typing import AsyncGenerator
from anthropic import AsyncAnthropic
from pydantic import BaseModel


class CallContext(BaseModel):
    """Context for a single call."""
    customer_name: str
    company_name: str
    purpose: str
    website_url: str | None = None
    project_context: str = ""
    project_dir: str | None = None
    call_direction: str = "inbound"  # "inbound" | "outbound"
    history: list[dict] = []


def is_sentence_boundary(text: str) -> bool:
    """Check if text ends at a natural sentence boundary for TTS chunking."""
    if not text.strip():
        return False
    last_char = text.rstrip()[-1]
    if last_char in '.!?':
        return True
    # Split on comma for long clauses (Hungarian sentences tend to be long)
    if last_char == ',' and len(text.strip()) > 40:
        return True
    return False


class ConversationAgent:
    """Claude-based conversation engine for voice calls."""

    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.client = AsyncAnthropic()
        self.model = model
        self.last_usage: dict | None = None

    def _build_system_prompt(self, ctx: CallContext) -> str:
        project_section = ""
        if ctx.project_context:
            project_section = f"\n\nProjekt információk:\n{ctx.project_context}"

        return f"""Te egy ügyfélszolgálati agent vagy a {ctx.company_name} nevében.

Kontextus:
- Ügyfél neve: {ctx.customer_name}
- Cél: {ctx.purpose}
{f'- Weboldal: {ctx.website_url}' if ctx.website_url else ''}{project_section}

A te feladatod:
1. Válaszolj az ügyfél kérdéseire a projektjével kapcsolatban
2. Ha módosítást vagy javítást kér, nyugtázd és foglald össze mit kér — a fejlesztő csapat meg fogja kapni
3. Ha nem érted pontosan mit kér, kérdezz vissza — inkább kérdezz egyet többet mint adj ki felesleges infót

Információforrások — fontossági sorrend:
1. Az openspec specifikáció (specs/ mappa) — ez az irányadó, MINDIG ebből indulj ki
2. A docs/ mappa — itt van a design dokumentáció, Figma/UI/UX leírások ha vannak
3. A forráskód — CSAK ha az ügyfél konkrét technikai kérdést tesz fel (pl. "miért kék az a gomb?", "hogyan működik a menü?"). Kerüld a kódba nézést ha az openspec vagy docs alapján válaszolni tudsz.

Szabályok:
- SOHA ne találj ki dolgokat magadtól! Ha nem tudod a választ, mondd hogy "Utánanézek" vagy "Ezt meg kell kérdeznem a csapattól"
- Rövid, természetes válaszok (1-2 mondat max) — ez telefon, nem chat
- Magyarul beszélj, természetesen, közvetlenül
- Ha az ügyfél búcsúzik vagy lezárja, zárd le udvariasan
- Ne ismételd magad, ne légy túl formális
- NE okoskodj és NE adj ki projekt részleteket amíg az ügyfél nem kérdez rá konkrétan!
- Ha módosítási kérés érkezik, erősítsd vissza mit értettél: "Értem, tehát X-et szeretné Y-ra módosítani, igaz?"
- A válaszod telefonon lesz felolvasva TTS-sel! NE használj markdown formázást, emojikat, kódot, URL-eket. Tiszta beszélt magyar nyelven válaszolj."""

    def _greeting_instruction(self, ctx: CallContext) -> str:
        """Return direction-aware greeting instruction."""
        if ctx.call_direction == "outbound":
            return (
                "(Te hívtad az ügyfelet, ő vette fel. Köszöntsd, mutatkozz be a cég nevében, "
                "mondd el hogy a hívás rögzítésre kerülhet, majd mondd el miért hívod: "
                f"{ctx.purpose}. Ne kérdezd hogy miben segíthetsz — te keresed őt.)"
            )
        project_name = ""
        if ctx.project_context:
            # Extract project name from context if available
            for line in ctx.project_context.split("\n"):
                if line.startswith("Kiválasztott projekt:"):
                    project_name = line.split(":", 1)[1].strip()
                    break
        if project_name:
            return (
                f"(Az ügyfél hívott a {project_name} projektjével kapcsolatban. "
                "Köszöntsd, mondd el a cég nevét, hogy a hívás rögzítésre kerülhet, "
                f"majd mondd el hogy elkészült a {project_name} projektje és kérdezd meg "
                "van-e kérdése vele kapcsolatban.)"
            )
        return (
            "(Az ügyfél hívott minket, te vetted fel. Köszöntsd, mondd el a cég nevét, "
            "hogy a hívás rögzítésre kerülhet, majd kérdezd meg miben segíthetsz.)"
        )

    async def get_greeting(self, ctx: CallContext) -> tuple[str, dict]:
        """Generate the opening greeting (non-streaming, greeting is short).

        Returns:
            Tuple of (text, usage_dict) where usage_dict has input_tokens and output_tokens.
        """
        response = await self.client.messages.create(
            model=self.model,
            system=self._build_system_prompt(ctx),
            messages=[{"role": "user", "content": self._greeting_instruction(ctx)}],
            max_tokens=150,
        )
        text = response.content[0].text
        usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
        ctx.history.append({"role": "assistant", "content": text})
        return text, usage

    async def get_greeting_stream(self, ctx: CallContext) -> AsyncGenerator[str, None]:
        """Stream the opening greeting sentence-by-sentence.

        Yields sentence chunks. After exhaustion, self.last_usage has token counts.
        """
        async with self.client.messages.stream(
            model=self.model,
            system=self._build_system_prompt(ctx),
            messages=[{"role": "user", "content": self._greeting_instruction(ctx)}],
            max_tokens=150,
        ) as stream:
            buffer = ""
            full_text = ""
            async for text in stream.text_stream:
                buffer += text
                full_text += text
                if is_sentence_boundary(buffer):
                    yield buffer.strip()
                    buffer = ""
            # Yield remaining buffer
            if buffer.strip():
                yield buffer.strip()

            # Get usage from final message
            final = await stream.get_final_message()
            self.last_usage = {
                "input_tokens": final.usage.input_tokens,
                "output_tokens": final.usage.output_tokens,
            }
            ctx.history.append({"role": "assistant", "content": full_text})

    async def respond(self, ctx: CallContext, customer_text: str) -> tuple[str, dict]:
        """Generate response (non-streaming, for backward compat).

        Returns:
            Tuple of (text, usage_dict).
        """
        ctx.history.append({"role": "user", "content": customer_text})

        response = await self.client.messages.create(
            model=self.model,
            system=self._build_system_prompt(ctx),
            messages=ctx.history,
            max_tokens=150,
        )
        text = response.content[0].text
        usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
        ctx.history.append({"role": "assistant", "content": text})
        return text, usage

    async def respond_stream(self, ctx: CallContext, customer_text: str) -> AsyncGenerator[str, None]:
        """Stream response sentence-by-sentence.

        Yields sentence chunks as Claude generates them.
        After exhaustion, self.last_usage has token counts.
        """
        ctx.history.append({"role": "user", "content": customer_text})

        async with self.client.messages.stream(
            model=self.model,
            system=self._build_system_prompt(ctx),
            messages=ctx.history,
            max_tokens=300,
        ) as stream:
            buffer = ""
            full_text = ""
            async for text in stream.text_stream:
                buffer += text
                full_text += text
                if is_sentence_boundary(buffer):
                    yield buffer.strip()
                    buffer = ""
            # Yield remaining buffer
            if buffer.strip():
                yield buffer.strip()

            # Get usage
            final = await stream.get_final_message()
            self.last_usage = {
                "input_tokens": final.usage.input_tokens,
                "output_tokens": final.usage.output_tokens,
            }
            ctx.history.append({"role": "assistant", "content": full_text})

    def should_hangup(self, agent_text: str) -> bool:
        """Check if the agent's response signals end of call."""
        endings = ["viszlát", "szép napot", "köszönöm a hívást", "további szép napot"]
        return any(w in agent_text.lower() for w in endings)

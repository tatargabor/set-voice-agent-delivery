"""Claude-powered conversation agent for voice calls."""

import asyncio
from typing import AsyncGenerator
from anthropic import AsyncAnthropic
from pydantic import BaseModel

from .i18n import (
    _SYSTEM_PROMPT, _GREETING_OUTBOUND, _GREETING_INBOUND_WITH_PROJECT,
    _GREETING_INBOUND_DEFAULT, _GREETING_SYSTEM, _FAREWELL_WORDS,
    _PROJECT_LABEL, _PROJECT_INFO_LABEL, get_text, lang,
)


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
    # Split on comma only for very long clauses to avoid mid-sentence cuts
    if last_char == ',' and len(text.strip()) > 80:
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
            label = get_text(_PROJECT_INFO_LABEL)
            project_section = f"\n\n{label}:\n{ctx.project_context}"

        extra_context = f'- Weboldal: {ctx.website_url}\n' if ctx.website_url else ''

        template = get_text(_SYSTEM_PROMPT)
        return template.format(
            company_name=ctx.company_name,
            customer_name=ctx.customer_name,
            purpose=ctx.purpose,
            extra_context=extra_context,
            project_section=project_section,
        )

    def _greeting_instruction(self, ctx: CallContext) -> str:
        """Return direction-aware greeting instruction."""
        if ctx.call_direction == "outbound":
            template = get_text(_GREETING_OUTBOUND)
            return template.format(purpose=ctx.purpose)

        project_name = ""
        if ctx.project_context:
            label = get_text(_PROJECT_LABEL)
            for line in ctx.project_context.split("\n"):
                if line.startswith(f"{label}:"):
                    project_name = line.split(":", 1)[1].strip()
                    break

        if project_name:
            template = get_text(_GREETING_INBOUND_WITH_PROJECT)
            return template.format(project_name=project_name)

        return get_text(_GREETING_INBOUND_DEFAULT)

    async def get_greeting(self, ctx: CallContext) -> tuple[str, dict]:
        """Generate the opening greeting (non-streaming, greeting is short)."""
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
        """Stream the opening greeting sentence-by-sentence."""
        from .config import get_settings
        greeting_model = get_settings().models.deep

        system = get_text(_GREETING_SYSTEM).format(company_name=ctx.company_name)

        async with self.client.messages.stream(
            model=greeting_model,
            system=system,
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
            if buffer.strip():
                yield buffer.strip()

            final = await stream.get_final_message()
            self.last_usage = {
                "input_tokens": final.usage.input_tokens,
                "output_tokens": final.usage.output_tokens,
            }
            ctx.history.append({"role": "assistant", "content": full_text})

    async def respond(self, ctx: CallContext, customer_text: str) -> tuple[str, dict]:
        """Generate response (non-streaming, for backward compat)."""
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
        """Stream response sentence-by-sentence."""
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
            if buffer.strip():
                yield buffer.strip()

            final = await stream.get_final_message()
            self.last_usage = {
                "input_tokens": final.usage.input_tokens,
                "output_tokens": final.usage.output_tokens,
            }
            ctx.history.append({"role": "assistant", "content": full_text})

    def should_hangup(self, agent_text: str) -> bool:
        """Check if the agent's response signals end of call."""
        endings = get_text(_FAREWELL_WORDS)
        return any(w in agent_text.lower() for w in endings)

"""Dual-layer response: fast ack (Haiku) + deep response (Opus/Sonnet) in parallel."""

import asyncio
from typing import AsyncGenerator
from anthropic import AsyncAnthropic

from .agent import CallContext, is_sentence_boundary

# Simple messages that don't need a fast ack
_SIMPLE_PATTERNS = {"igen", "nem", "szia", "helló", "halló", "ok", "oké", "jó", "köszönöm", "köszi", "meg", "megkaptam"}


def _is_simple(text: str) -> bool:
    """Check if customer message is too simple to warrant a fast ack."""
    words = text.strip().lower().rstrip(".!?,")
    return len(words) < 15 or words in _SIMPLE_PATTERNS


class ResponseLayers:
    """Dual-layer response orchestrator.

    Fast Layer (Haiku): immediate acknowledgment (~300ms)
    Deep Layer (configurable): substantive streaming response
    """

    def __init__(
        self,
        fast_model: str = "claude-haiku-4-5",
        deep_model: str = "claude-sonnet-4-6",
    ):
        self.client = AsyncAnthropic()
        self.fast_model = fast_model
        self.deep_model = deep_model
        self.last_usage: dict | None = None
        self._fast_usage: dict | None = None

    async def _fast_ack(self, customer_text: str, company_name: str) -> str:
        """Generate immediate acknowledgment via Haiku."""
        response = await self.client.messages.create(
            model=self.fast_model,
            system=f"Röviden nyugtázd amit az ügyfél mondott. Max 5 szó. Magyarul. Ne ígérj semmit, csak nyugtázd. Cég: {company_name}.",
            messages=[{"role": "user", "content": customer_text}],
            max_tokens=30,
        )
        text = response.content[0].text
        self._fast_usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return text

    async def _deep_response_stream(
        self, ctx: CallContext, system_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Generate substantive streaming response via deep model."""
        async with self.client.messages.stream(
            model=self.deep_model,
            system=system_prompt,
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

    async def respond(
        self, ctx: CallContext, customer_text: str, system_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Dual-layer response: fast ack then deep streaming response.

        For simple messages (greetings, yes/no), skips fast ack.

        Yields sentence chunks. After exhaustion:
        - self.last_usage has deep layer token counts
        - self._fast_usage has fast layer token counts (if used)
        """
        ctx.history.append({"role": "user", "content": customer_text})

        if _is_simple(customer_text):
            # Simple message — skip fast ack, go straight to deep
            full_text = ""
            async for sentence in self._deep_response_stream(ctx, system_prompt):
                full_text += sentence + " "
                yield sentence
            ctx.history.append({"role": "assistant", "content": full_text.strip()})
            return

        # Fire both in parallel
        fast_task = asyncio.create_task(
            self._fast_ack(customer_text, ctx.company_name)
        )

        # Collect deep response sentences while fast ack is running
        deep_sentences = []

        async def _collect_deep():
            async for sentence in self._deep_response_stream(ctx, system_prompt):
                deep_sentences.append(sentence)

        deep_task = asyncio.create_task(_collect_deep())

        # Yield fast ack first (should arrive in ~300ms)
        fast_text = await fast_task
        yield fast_text

        # Wait for deep to finish
        await deep_task

        # Yield deep response sentences
        for sentence in deep_sentences:
            yield sentence

        # Record both in history as one assistant message
        full_text = fast_text + " " + " ".join(deep_sentences)
        ctx.history.append({"role": "assistant", "content": full_text.strip()})

"""Dual-layer response: fast ack (Haiku) + deep response (Opus/Sonnet) in parallel."""

import asyncio
import time
from pathlib import Path
from typing import AsyncGenerator
from anthropic import AsyncAnthropic
import structlog

from .agent import CallContext, is_sentence_boundary
from .agent_tools import TOOL_DEFINITIONS, execute_tool
from .agent_cache import get_or_create_cache
from .config import get_settings
from .local_agent import research

log = structlog.get_logger()

from .i18n import (
    _SIMPLE_PATTERNS, _RESEARCH_KEYWORDS, _FAST_ACK, _THINKING_MESSAGES,
    _RESEARCH_PREFIX, _VOICE_FOLLOWUP, _VOICE_NOT_FOUND, get_text,
)


def _is_research_question(text: str) -> bool:
    """Check if the question likely needs deep project research."""
    lower = text.strip().lower()
    keywords = get_text(_RESEARCH_KEYWORDS)
    return any(kw in lower for kw in keywords)


def _is_simple(text: str) -> bool:
    """Check if customer message is too simple to warrant a fast ack."""
    words = text.strip().lower().rstrip(".!?,")
    return len(words) < 15 or words in get_text(_SIMPLE_PATTERNS)


class ResponseLayers:
    """Dual-layer response orchestrator.

    Fast Layer (Haiku): immediate acknowledgment (~300ms)
    Deep Layer (configurable): substantive streaming response
    """

    def __init__(
        self,
        fast_model: str | None = None,
        deep_model: str | None = None,
    ):
        settings = get_settings()
        self.client = AsyncAnthropic()
        self.fast_model = fast_model or settings.models.fast
        self.deep_model = deep_model or settings.models.deep
        self.last_usage: dict | None = None
        self._fast_usage: dict | None = None
        self.tool_calls: list[dict] = []  # Logged per-response

    async def _fast_ack(self, customer_text: str, company_name: str) -> str:
        """Generate immediate acknowledgment via Haiku."""
        response = await self.client.messages.create(
            model=self.fast_model,
            system=get_text(_FAST_ACK).format(company_name=company_name),
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
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=ctx.history,
            max_tokens=get_settings().voice.max_tokens_stream,
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
                "cache_read_input_tokens": getattr(final.usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_input_tokens": getattr(final.usage, "cache_creation_input_tokens", 0) or 0,
            }

    async def _deep_response_with_tools(
        self, ctx: CallContext, system_prompt: str, project_dir: Path
    ) -> list[str]:
        """Deep response with tool_use loop. Returns list of sentence chunks.

        Non-streaming because tool_use requires synchronous message loop.
        Falls back to streaming if no tools are needed.
        """
        self.tool_calls = []
        messages = list(ctx.history)  # Copy
        total_start = time.monotonic()
        settings = get_settings()
        _TOOL_TIMEOUT = float(settings.research.tool_timeout_sec)

        for _iteration in range(5):  # Max 5 tool rounds
            elapsed = time.monotonic() - total_start
            if elapsed > _TOOL_TIMEOUT:
                log.warning("tool_loop_timeout", elapsed=elapsed)
                break

            response = await self.client.messages.create(
                model=self.deep_model,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                messages=messages,
                max_tokens=settings.voice.max_tokens_tool_use,
                tools=TOOL_DEFINITIONS,
            )

            self.last_usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            }

            if response.stop_reason == "tool_use":
                # Execute tool calls
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_start = time.monotonic()
                        result = execute_tool(block.name, block.input, project_dir)
                        tool_ms = int((time.monotonic() - tool_start) * 1000)
                        log.info("tool_executed", tool=block.name, input=block.input, ms=tool_ms)
                        self.tool_calls.append({
                            "tool": block.name,
                            "input": block.input,
                            "ms": tool_ms,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Final text response — split into sentences
                text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text += block.text
                sentences = []
                buffer = ""
                for char in text:
                    buffer += char
                    if is_sentence_boundary(buffer):
                        sentences.append(buffer.strip())
                        buffer = ""
                if buffer.strip():
                    sentences.append(buffer.strip())
                # Voice limit: max N sentences, suggest follow-up
                _MAX_VOICE_SENTENCES = settings.voice.max_sentences
                if len(sentences) > _MAX_VOICE_SENTENCES:
                    sentences = sentences[:_MAX_VOICE_SENTENCES]
                    sentences.append(get_text(_VOICE_FOLLOWUP))
                return sentences

        # Timeout fallback — return whatever text blocks we got from last response
        return [get_text(_VOICE_NOT_FOUND)]

    async def _deep_response_with_agent(
        self, ctx: CallContext, project_dir: Path
    ) -> list[str]:
        """Deep response via local agent. Returns list of sentence chunks."""
        self.tool_calls = []
        customer_text = ctx.history[-1]["content"] if ctx.history else ""

        cache = get_or_create_cache(project_dir)
        answer = await research(customer_text, project_dir, cache)

        # Split into sentences and apply voice limit
        settings = get_settings()
        sentences = []
        buffer = ""
        for char in answer:
            buffer += char
            if is_sentence_boundary(buffer):
                sentences.append(buffer.strip())
                buffer = ""
        if buffer.strip():
            sentences.append(buffer.strip())

        max_s = settings.voice.max_sentences
        if len(sentences) > max_s:
            sentences = sentences[:max_s]
            sentences.append(get_text(_VOICE_FOLLOWUP))

        return sentences

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
            # Simple message — skip fast ack, go straight to deep (no tools needed)
            full_text = ""
            async for sentence in self._deep_response_stream(ctx, system_prompt):
                full_text += sentence + " "
                yield sentence
            ctx.history.append({"role": "assistant", "content": full_text.strip()})
            return

        settings = get_settings()
        mode = settings.research.mode
        has_project = ctx.project_dir and Path(ctx.project_dir).exists()
        is_research = _is_research_question(customer_text)

        # For research questions: skip fast ack (it would say something dumb
        # before tools run), just say "utánanézek" and go straight to tool_use
        if is_research and has_project:
            yield get_text(_RESEARCH_PREFIX)

            pdir = Path(ctx.project_dir)
            use_agent = mode == "local_agent" or mode == "auto"
            if use_agent:
                sentences = await self._deep_response_with_agent(ctx, pdir)
            else:
                sentences = await self._deep_response_with_tools(ctx, system_prompt, pdir)

            full_parts = [get_text(_RESEARCH_PREFIX)] + sentences
            for sentence in sentences:
                yield sentence
            ctx.history.append({"role": "assistant", "content": " ".join(full_parts).strip()})
            return

        # Non-research: fire fast ack + deep streaming in parallel
        fast_task = asyncio.create_task(
            self._fast_ack(customer_text, ctx.company_name)
        )

        deep_sentences = []
        deep_done = asyncio.Event()

        async def _collect_deep():
            if has_project:
                pdir = Path(ctx.project_dir)
                use_agent = mode == "local_agent" or (mode == "auto" and is_research)
                if use_agent:
                    sentences = await self._deep_response_with_agent(ctx, pdir)
                else:
                    sentences = await self._deep_response_with_tools(ctx, system_prompt, pdir)
                deep_sentences.extend(sentences)
            else:
                async for sentence in self._deep_response_stream(ctx, system_prompt):
                    deep_sentences.append(sentence)
            deep_done.set()

        deep_task = asyncio.create_task(_collect_deep())

        # Yield fast ack first (should arrive in ~300ms)
        fast_text = await fast_task
        yield fast_text

        # Wait for deep response — max 1 thinking message after 3 seconds
        if not deep_done.is_set():
            try:
                await asyncio.wait_for(deep_done.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                yield get_text(_THINKING_MESSAGES)[0]
                # Now just wait for it to finish, no more thinking messages
                await deep_done.wait()

        # Yield deep response sentences
        for sentence in deep_sentences:
            yield sentence

        # Record in history
        all_parts = [fast_text] + deep_sentences
        ctx.history.append({"role": "assistant", "content": " ".join(all_parts).strip()})

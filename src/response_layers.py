"""Dual-layer response: fast ack (Haiku) + deep response (Opus/Sonnet) in parallel."""

import asyncio
import time
from pathlib import Path
from typing import AsyncGenerator
from anthropic import AsyncAnthropic
import structlog

from .agent import CallContext, is_sentence_boundary
from .agent_tools import TOOL_DEFINITIONS, execute_tool

log = structlog.get_logger()

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
        self.tool_calls: list[dict] = []  # Logged per-response

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
        _TOOL_TIMEOUT = 15.0

        for _iteration in range(5):  # Max 5 tool rounds
            elapsed = time.monotonic() - total_start
            if elapsed > _TOOL_TIMEOUT:
                log.warning("tool_loop_timeout", elapsed=elapsed)
                break

            response = await self.client.messages.create(
                model=self.deep_model,
                system=system_prompt,
                messages=messages,
                max_tokens=300,
                tools=TOOL_DEFINITIONS,
            )

            self.last_usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
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
                return sentences

        # Timeout fallback — return whatever text blocks we got from last response
        return ["Sajnos nem sikerült az információt megtalálni."]

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

        # Fire both in parallel
        fast_task = asyncio.create_task(
            self._fast_ack(customer_text, ctx.company_name)
        )

        # Collect deep response sentences while fast ack is running
        deep_sentences = []
        deep_done = asyncio.Event()

        async def _collect_deep():
            if ctx.project_dir and Path(ctx.project_dir).exists():
                # Use tool_use loop for project-aware responses
                sentences = await self._deep_response_with_tools(
                    ctx, system_prompt, Path(ctx.project_dir)
                )
                deep_sentences.extend(sentences)
            else:
                async for sentence in self._deep_response_stream(ctx, system_prompt):
                    deep_sentences.append(sentence)
            deep_done.set()

        deep_task = asyncio.create_task(_collect_deep())

        # Yield fast ack first (should arrive in ~300ms)
        fast_text = await fast_task
        yield fast_text

        # Wait for deep response with periodic "still thinking" updates
        _THINKING = ["Egy pillanat, utánanézek...", "Még dolgozom rajta..."]
        thinking_idx = 0
        while not deep_done.is_set():
            try:
                await asyncio.wait_for(deep_done.wait(), timeout=4.0)
            except asyncio.TimeoutError:
                if thinking_idx < len(_THINKING):
                    yield _THINKING[thinking_idx]
                    thinking_idx += 1

        # Yield deep response sentences
        for sentence in deep_sentences:
            yield sentence

        # Record in history
        all_parts = [fast_text] + deep_sentences
        ctx.history.append({"role": "assistant", "content": " ".join(all_parts).strip()})

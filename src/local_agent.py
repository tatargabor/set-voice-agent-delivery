"""Local agent — autonomous project research for voice calls."""

import asyncio
import time
from pathlib import Path

import structlog
from anthropic import AsyncAnthropic

from .agent_cache import AgentCache, get_or_create_cache
from .agent_tools import TOOL_DEFINITIONS, execute_tool
from .config import get_settings
from .i18n import _RESEARCH_FALLBACK, get_text

log = structlog.get_logger()

# Truncate tool results to keep agent context small
_MAX_TOOL_RESULT_CHARS = 1000


def _build_agent_prompt(cache: AgentCache) -> str:
    """Build a research-focused system prompt with cached context."""
    cache_context = cache.to_context_string()
    return f"""Te egy projekt kutató agent vagy. Feladatod: a megadott kérdést megválaszolni a projekt fájljai alapján.

Projekt könyvtár: {cache.project_dir}

{cache_context}

Szabályok:
- Max 2 mondatban válaszolj — az eredményed telefonon lesz felolvasva TTS-sel
- Foglald össze a lényeget, ne olvass fel fájlokat szó szerint
- Ha nem találsz választ, mondd meg őszintén
- Használd a tool-okat ha a cache-ben nincs elég info
- NE használj markdown formázást, csillagokat, emojikat, kódot. Tiszta beszélt magyar nyelven válaszolj."""


async def research(question: str, project_dir: Path, cache: AgentCache | None = None) -> str:
    """Investigate a project and return a concise voice-ready answer.

    Returns a short text answer (max 2-3 sentences).
    """
    settings = get_settings()
    if cache is None:
        cache = get_or_create_cache(project_dir)

    client = AsyncAnthropic()
    system_prompt = _build_agent_prompt(cache)
    messages = [{"role": "user", "content": question}]

    total_start = time.monotonic()
    timeout = float(settings.research.agent_timeout_sec)
    max_iter = settings.research.agent_max_iterations
    last_text = ""

    for iteration in range(max_iter):
        elapsed = time.monotonic() - total_start
        if elapsed > timeout:
            log.warning("local_agent_timeout", elapsed=elapsed, iteration=iteration)
            break

        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=settings.models.agent,
                    system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                    messages=messages,
                    max_tokens=settings.voice.max_tokens_agent,
                    tools=TOOL_DEFINITIONS,
                ),
                timeout=timeout - elapsed,
            )
        except asyncio.TimeoutError:
            log.warning("local_agent_api_timeout", iteration=iteration)
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input, project_dir)
                    # Truncate tool results
                    if len(result) > _MAX_TOOL_RESULT_CHARS:
                        result = result[:_MAX_TOOL_RESULT_CHARS] + "\n[...csonkolva]"
                    log.info("local_agent_tool", tool=block.name, input=block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            # Final text response
            last_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    last_text += block.text

            # Cache key findings from the answer
            if last_text and len(last_text) > 20:
                cache.add_finding(f"Q: {question[:80]} → {last_text[:120]}")

            return last_text

    # Fallback if we hit timeout/max iterations
    if last_text:
        cache.add_finding(f"Q: {question[:80]} → {last_text[:120]}")
        return last_text
    return get_text(_RESEARCH_FALLBACK)

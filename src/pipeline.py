"""Call pipeline — orchestrates STT → Claude → TTS audio loop."""

import asyncio
import time
import structlog

from .agent import ConversationAgent, CallContext
from .metrics import CallMetrics
from .response_layers import ResponseLayers
from .state import CallState, CallStateMachine
from .providers.base import STTProvider, TTSProvider, TelephonyProvider, TranscriptEvent

log = structlog.get_logger()

# Sentinel value to signal end of a turn's sentence chunks
_TURN_END = "__TURN_END__"


class CallPipeline:
    """Orchestrates the full voice call: audio in → STT → Claude → TTS → audio out."""

    def __init__(
        self,
        stt: STTProvider,
        tts: TTSProvider,
        telephony: TelephonyProvider,
        agent: ConversationAgent,
        metrics: CallMetrics | None = None,
    ):
        self.stt = stt
        self.tts = tts
        self.telephony = telephony
        self.agent = agent
        self.metrics = metrics
        self.response_layers: ResponseLayers | None = None
        self.state_machine = CallStateMachine()
        self._state_lock = asyncio.Lock()

        # Inter-task queues
        self._stt_queue: asyncio.Queue[TranscriptEvent] = asyncio.Queue()
        self._tts_queue: asyncio.Queue[str] = asyncio.Queue()

        # Barge-in control
        self._tts_cancel_event = asyncio.Event()

    async def _transition(self, new_state: CallState, reason: str = "") -> None:
        """Thread-safe state transition."""
        async with self._state_lock:
            self.state_machine.transition(new_state, reason)

    @property
    def _state(self) -> CallState:
        return self.state_machine.state

    async def _stt_loop(self, call_id: str) -> None:
        """Read audio from telephony → STT → put TranscriptEvents on queue."""
        audio_stream = self.telephony.get_audio_stream(call_id)

        async for event in self.stt.transcribe_stream(audio_stream):
            if not event.text.strip():
                continue

            if self._state == CallState.SPEAKING:
                # Barge-in: customer spoke while agent was speaking
                log.info("barge_in_detected", transcript=event.text, is_interim=event.is_interim)
                self._tts_cancel_event.set()
                await self.telephony.clear_audio(call_id)
                if self.metrics:
                    self.metrics.barge_in_count += 1
                await self._transition(CallState.LISTENING, reason="barge-in")

            if self._state == CallState.LISTENING:
                # New utterance — transition to PROCESSING
                await self._transition(CallState.PROCESSING, reason="interim" if event.is_interim else "endpoint detected")
                await self._stt_queue.put(event)
            elif self._state == CallState.PROCESSING and not event.is_interim:
                # Final arriving while PROCESSING — only pass if it's an
                # interim→final upgrade (llm_loop handles the match/miss).
                # Don't transition again, just enqueue the final event.
                await self._stt_queue.put(event)

            if self.state_machine.is_ended:
                break

    async def _llm_loop(self, ctx: CallContext) -> None:
        """Get TranscriptEvents → speculative or direct LLM response → TTS queue.

        On interim events: start LLM speculatively.
        On final events: if text matches interim, use existing result; otherwise cancel + restart.
        """
        system_prompt = self.agent._build_system_prompt(ctx)

        # Speculative state
        speculative_task: asyncio.Task | None = None
        speculative_text: str | None = None
        speculative_sentences: list[str] = []
        speculative_done = asyncio.Event()

        while not self.state_machine.is_ended:
            try:
                event = await asyncio.wait_for(self._stt_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            log.info("processing_transcript", text=event.text, is_interim=event.is_interim)

            if event.is_interim:
                # Start speculative LLM — don't send to TTS yet, just collect
                speculative_text = event.text
                speculative_sentences.clear()
                speculative_done.clear()

                async def _speculative_collect(text: str):
                    try:
                        if self.response_layers:
                            gen = self.response_layers.respond(ctx, text, system_prompt)
                        else:
                            gen = self.agent.respond_stream(ctx, text)
                        async for sentence in gen:
                            speculative_sentences.append(sentence)
                    finally:
                        speculative_done.set()

                speculative_task = asyncio.create_task(_speculative_collect(event.text))
                log.info("speculative_llm_started", text=event.text)
                continue

            # Final event — decide whether to use speculative result or restart
            t0 = time.monotonic()

            if speculative_task and speculative_text == event.text:
                # Interim matched final — use speculative result
                log.info("speculative_hit", text=event.text)
                await speculative_done.wait()
                # Send collected sentences to TTS
                full_response = ""
                for i, sentence in enumerate(speculative_sentences):
                    if i == 0:
                        elapsed_ms = int((time.monotonic() - t0) * 1000)
                        log.info("first_sentence", text=sentence, latency_ms=elapsed_ms)
                        if self.metrics:
                            self.metrics.response_times_ms.append(elapsed_ms)
                    else:
                        log.debug("sentence_chunk", text=sentence)
                    full_response += sentence + " "
                    await self._tts_queue.put(sentence)
            else:
                if speculative_task:
                    # Interim didn't match — cancel speculative work
                    log.info("speculative_miss", interim=speculative_text, final=event.text)
                    speculative_task.cancel()
                    try:
                        await speculative_task
                    except asyncio.CancelledError:
                        pass
                    # Clear TTS queue and cancel any playing audio
                    self._tts_cancel_event.set()
                    while not self._tts_queue.empty():
                        try:
                            self._tts_queue.get_nowait()
                            self._tts_queue.task_done()
                        except asyncio.QueueEmpty:
                            break
                    self._tts_cancel_event.clear()
                    # Undo the interim's history entry (respond() appends to ctx.history)
                    if ctx.history and ctx.history[-1].get("role") == "assistant":
                        ctx.history.pop()
                    if ctx.history and ctx.history[-1].get("content") == speculative_text:
                        ctx.history.pop()

                # Stream response directly to TTS as sentences arrive
                full_response = ""
                first_chunk = True
                if self.response_layers:
                    gen = self.response_layers.respond(ctx, event.text, system_prompt)
                else:
                    gen = self.agent.respond_stream(ctx, event.text)
                async for sentence in gen:
                    if first_chunk:
                        elapsed_ms = int((time.monotonic() - t0) * 1000)
                        log.info("first_sentence", text=sentence, latency_ms=elapsed_ms)
                        if self.metrics:
                            self.metrics.response_times_ms.append(elapsed_ms)
                        first_chunk = False
                    else:
                        log.debug("sentence_chunk", text=sentence)
                    full_response += sentence + " "
                    await self._tts_queue.put(sentence)

            # Reset speculative state
            speculative_task = None
            speculative_text = None
            speculative_sentences.clear()

            # Signal end of this turn's chunks
            await self._tts_queue.put(_TURN_END)

            # Track usage
            self._track_usage()

            if self.metrics:
                self.metrics.turn_count += 1

            log.info("agent_response_complete", text=full_response.strip())

            if self.agent.should_hangup(full_response):
                await self._tts_queue.join()
                await asyncio.sleep(3)
                await self._transition(CallState.ENDED, reason="agent farewell")
                break

    def _track_usage(self) -> None:
        """Track Claude API usage from response layers or agent."""
        if self.response_layers:
            if self.response_layers.last_usage and self.metrics:
                self.metrics.add_claude_usage(
                    self.response_layers.last_usage["input_tokens"],
                    self.response_layers.last_usage["output_tokens"],
                )
                self.metrics.add_cache_usage(
                    self.response_layers.last_usage.get("cache_read_input_tokens", 0),
                    self.response_layers.last_usage.get("cache_creation_input_tokens", 0),
                )
            if self.response_layers._fast_usage and self.metrics:
                self.metrics.add_claude_usage(
                    self.response_layers._fast_usage["input_tokens"],
                    self.response_layers._fast_usage["output_tokens"],
                )
                self.response_layers._fast_usage = None
            if self.response_layers.tool_calls and self.metrics:
                self.metrics.add_tool_calls(self.response_layers.tool_calls)
                self.response_layers.tool_calls = []
        elif self.agent.last_usage and self.metrics:
            self.metrics.add_claude_usage(
                self.agent.last_usage["input_tokens"],
                self.agent.last_usage["output_tokens"],
            )

    async def _tts_loop(self, call_id: str) -> None:
        """Get sentence chunks → TTS → send audio to telephony.

        Processes multiple sentence chunks per turn. Only sends mark
        and transitions to LISTENING after the turn-end sentinel.
        """
        while not self.state_machine.is_ended:
            try:
                text = await asyncio.wait_for(self._tts_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if text == _TURN_END:
                # End of turn — wait for playback and transition to LISTENING
                self._tts_queue.task_done()
                if not self._tts_cancel_event.is_set() and not self.state_machine.is_ended:
                    await self.telephony.send_mark(call_id)
                    if self._state == CallState.SPEAKING:
                        await self._transition(CallState.LISTENING, reason="tts complete")
                continue

            if self.metrics:
                self.metrics.tts_chars += len(text)

            # Transition to SPEAKING on first chunk of a turn
            if self._state == CallState.PROCESSING and not self.state_machine.is_ended:
                await self._transition(CallState.SPEAKING, reason="tts start")
                self._tts_cancel_event.clear()
            elif self._state not in (CallState.SPEAKING, CallState.PROCESSING) and not self.state_machine.is_ended:
                # Stale TTS chunk from cancelled turn — skip it
                log.info("tts_skipped_stale", state=self._state.value, text=text[:50])
                self._tts_queue.task_done()
                continue

            try:
                async for audio_chunk in self.tts.synthesize_stream(text):
                    if self._tts_cancel_event.is_set():
                        log.info("tts_cancelled", reason="barge-in")
                        break
                    await self.telephony.send_audio(call_id, audio_chunk)
            finally:
                self._tts_queue.task_done()

    async def run(self, ctx: CallContext, call_id: str) -> None:
        """Run the full call pipeline."""
        log.info("pipeline_start", customer=ctx.customer_name, call_id=call_id)

        # Connect providers in this event loop
        await self.stt.connect()
        await self.tts.connect()

        # Stream greeting sentence-by-sentence — send audio immediately, no sleep
        async for sentence in self.agent.get_greeting_stream(ctx):
            log.info("greeting_chunk", text=sentence)
            if self.metrics:
                self.metrics.tts_chars += len(sentence)
            async for audio_chunk in self.tts.synthesize_stream(sentence):
                await self.telephony.send_audio(call_id, audio_chunk)

        # Track greeting usage
        if self.agent.last_usage and self.metrics:
            self.metrics.add_claude_usage(
                self.agent.last_usage["input_tokens"],
                self.agent.last_usage["output_tokens"],
            )

        # Transition to LISTENING immediately — Twilio buffers and plays the greeting
        # while we already start listening. If the customer speaks during the greeting,
        # the STT loop picks it up (barge-in handles it).
        await self._transition(CallState.LISTENING, reason="greeting sent")

        # Run the three concurrent loops
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._stt_loop(call_id))
                tg.create_task(self._llm_loop(ctx))
                tg.create_task(self._tts_loop(call_id))
        except* Exception as eg:
            for exc in eg.exceptions:
                if not isinstance(exc, asyncio.CancelledError):
                    log.error("pipeline_error", error=str(exc), type=type(exc).__name__)
                    if self.metrics:
                        self.metrics.add_error(type(exc).__name__, str(exc))
        finally:
            await self.stt.disconnect()
            await self.tts.disconnect()

        # Hang up after pipeline ends
        if self.state_machine.is_ended:
            try:
                await self.telephony.hangup(call_id)
                log.info("call_hangup", call_id=call_id)
            except Exception:
                pass

        log.info("pipeline_end", call_id=call_id, turns=len(ctx.history))

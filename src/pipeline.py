"""Call pipeline — orchestrates STT → Claude → TTS audio loop."""

import asyncio
import time
import structlog

from .agent import ConversationAgent, CallContext
from .metrics import CallMetrics
from .response_layers import ResponseLayers
from .state import CallState, CallStateMachine
from .providers.base import STTProvider, TTSProvider, TelephonyProvider

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
        self._stt_queue: asyncio.Queue[str] = asyncio.Queue()
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
        """Read audio from telephony → STT → put transcripts on queue."""
        audio_stream = self.telephony.get_audio_stream(call_id)

        async for transcript in self.stt.transcribe_stream(audio_stream):
            if not transcript.strip():
                continue

            if self._state == CallState.SPEAKING:
                # Barge-in: customer spoke while agent was speaking
                log.info("barge_in_detected", transcript=transcript)
                self._tts_cancel_event.set()
                await self.telephony.clear_audio(call_id)
                if self.metrics:
                    self.metrics.barge_in_count += 1
                await self._transition(CallState.LISTENING, reason="barge-in")

            if self._state == CallState.LISTENING:
                await self._transition(CallState.PROCESSING, reason="endpoint detected")
                await self._stt_queue.put(transcript)

            if self.state_machine.is_ended:
                break

    async def _llm_loop(self, ctx: CallContext) -> None:
        """Get transcripts → dual-layer or streaming response → TTS queue."""
        system_prompt = self.agent._build_system_prompt(ctx)

        while not self.state_machine.is_ended:
            try:
                transcript = await asyncio.wait_for(self._stt_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            log.info("processing_transcript", text=transcript)

            t0 = time.monotonic()
            full_response = ""
            first_chunk = True

            # Use dual-layer if available, otherwise streaming agent
            if self.response_layers:
                response_gen = self.response_layers.respond(ctx, transcript, system_prompt)
            else:
                response_gen = self.agent.respond_stream(ctx, transcript)

            async for sentence in response_gen:
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

            # Signal end of this turn's chunks
            await self._tts_queue.put(_TURN_END)

            # Track usage from response layers or agent
            if self.response_layers:
                if self.response_layers.last_usage and self.metrics:
                    self.metrics.add_claude_usage(
                        self.response_layers.last_usage["input_tokens"],
                        self.response_layers.last_usage["output_tokens"],
                    )
                # Also track fast ack usage
                if self.response_layers._fast_usage and self.metrics:
                    self.metrics.add_claude_usage(
                        self.response_layers._fast_usage["input_tokens"],
                        self.response_layers._fast_usage["output_tokens"],
                    )
                    self.response_layers._fast_usage = None
            elif self.agent.last_usage and self.metrics:
                self.metrics.add_claude_usage(
                    self.agent.last_usage["input_tokens"],
                    self.agent.last_usage["output_tokens"],
                )

            if self.metrics:
                self.metrics.turn_count += 1

            log.info("agent_response_complete", text=full_response.strip())

            if self.agent.should_hangup(full_response):
                await self._tts_queue.join()
                await asyncio.sleep(3)
                await self._transition(CallState.ENDED, reason="agent farewell")
                break

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
            if self._state != CallState.SPEAKING and not self.state_machine.is_ended:
                await self._transition(CallState.SPEAKING, reason="tts start")
                self._tts_cancel_event.clear()

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

        # Stream greeting sentence-by-sentence
        greeting_audio_bytes = 0
        async for sentence in self.agent.get_greeting_stream(ctx):
            log.info("greeting_chunk", text=sentence)
            if self.metrics:
                self.metrics.tts_chars += len(sentence)
            async for audio_chunk in self.tts.synthesize_stream(sentence):
                await self.telephony.send_audio(call_id, audio_chunk)
                greeting_audio_bytes += len(audio_chunk)

        # Track greeting usage
        if self.agent.last_usage and self.metrics:
            self.metrics.add_claude_usage(
                self.agent.last_usage["input_tokens"],
                self.agent.last_usage["output_tokens"],
            )

        # Wait for greeting playback
        audio_data_bytes = max(0, greeting_audio_bytes - 44)
        greeting_duration = audio_data_bytes / 8000
        wait_time = max(0, greeting_duration - 1.0)
        await asyncio.sleep(wait_time)
        await self._transition(CallState.LISTENING, reason="greeting complete")

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

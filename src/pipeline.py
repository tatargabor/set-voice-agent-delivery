"""Call pipeline — orchestrates STT → Claude → TTS audio loop."""

import asyncio
import time
import structlog

from .agent import ConversationAgent, CallContext
from .metrics import CallMetrics
from .state import CallState, CallStateMachine
from .providers.base import STTProvider, TTSProvider, TelephonyProvider

log = structlog.get_logger()


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
                if self.metrics:
                    self.metrics.barge_in_count += 1
                await self._transition(CallState.LISTENING, reason="barge-in")

            if self._state == CallState.LISTENING:
                await self._transition(CallState.PROCESSING, reason="endpoint detected")
                await self._stt_queue.put(transcript)

            if self.state_machine.is_ended:
                break

    async def _llm_loop(self, ctx: CallContext) -> None:
        """Get transcripts → Claude → put responses on TTS queue."""
        while not self.state_machine.is_ended:
            try:
                transcript = await asyncio.wait_for(self._stt_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            log.info("processing_transcript", text=transcript)

            t0 = time.monotonic()
            response, usage = await self.agent.respond(ctx, transcript)
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            log.info("agent_response", text=response)

            if self.metrics:
                self.metrics.add_claude_usage(usage["input_tokens"], usage["output_tokens"])
                self.metrics.response_times_ms.append(elapsed_ms)
                self.metrics.turn_count += 1

            if self.agent.should_hangup(response):
                await self._tts_queue.put(response)
                # Wait for TTS to finish the farewell before ending
                await self._tts_queue.join()
                await self._transition(CallState.ENDED, reason="agent farewell")
                break

            await self._tts_queue.put(response)

    async def _tts_loop(self, call_id: str) -> None:
        """Get response text → TTS → send audio to telephony."""
        while not self.state_machine.is_ended:
            try:
                text = await asyncio.wait_for(self._tts_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if self.metrics:
                self.metrics.tts_chars += len(text)

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

            if not self._tts_cancel_event.is_set() and not self.state_machine.is_ended:
                await self._transition(CallState.LISTENING, reason="tts complete")

    async def run(self, ctx: CallContext, call_id: str) -> None:
        """Run the full call pipeline.

        Args:
            ctx: The call context with customer info and conversation history.
            call_id: The telephony call ID (e.g. Twilio Call SID).
        """
        log.info("pipeline_start", customer=ctx.customer_name, call_id=call_id)

        # Connect providers in this event loop (important for WebSocket sessions)
        await self.stt.connect()
        await self.tts.connect()

        # Generate and speak greeting
        greeting, greeting_usage = await self.agent.get_greeting(ctx)
        log.info("greeting_generated", text=greeting)

        if self.metrics:
            self.metrics.add_claude_usage(greeting_usage["input_tokens"], greeting_usage["output_tokens"])
            self.metrics.tts_chars += len(greeting)

        async for audio_chunk in self.tts.synthesize_stream(greeting):
            await self.telephony.send_audio(call_id, audio_chunk)

        await self._transition(CallState.LISTENING, reason="greeting complete")

        # Run the three concurrent loops
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._stt_loop(call_id))
                tg.create_task(self._llm_loop(ctx))
                tg.create_task(self._tts_loop(call_id))
        except* Exception as eg:
            # Log any errors from the task group
            for exc in eg.exceptions:
                if not isinstance(exc, asyncio.CancelledError):
                    log.error("pipeline_error", error=str(exc), type=type(exc).__name__)
                    if self.metrics:
                        self.metrics.add_error(type(exc).__name__, str(exc))
        finally:
            await self.stt.disconnect()
            await self.tts.disconnect()

        log.info("pipeline_end", call_id=call_id, turns=len(ctx.history))

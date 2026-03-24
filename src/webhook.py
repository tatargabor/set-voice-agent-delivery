"""FastAPI webhook server for Twilio call control and Media Streams."""

import asyncio
import base64
import json
import structlog
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response

from .agent import ConversationAgent, CallContext
from .pipeline import CallPipeline
from .providers.soniox_stt import SonioxSTTProvider
from .providers.google_tts import GoogleTTSProvider
from .providers.twilio_provider import TwilioTelephonyProvider

log = structlog.get_logger()

app = FastAPI()

# Shared state — set by call_runner before starting the server
_call_context: CallContext | None = None
_pipeline: CallPipeline | None = None
_telephony: TwilioTelephonyProvider | None = None
_call_id: str | None = None
_pipeline_done: asyncio.Event | None = None


def configure(
    ctx: CallContext,
    pipeline: CallPipeline,
    telephony: TwilioTelephonyProvider,
    call_id: str,
    done_event: asyncio.Event,
) -> None:
    """Configure the webhook server with call state."""
    global _call_context, _pipeline, _telephony, _call_id, _pipeline_done
    _call_context = ctx
    _pipeline = pipeline
    _telephony = telephony
    _call_id = call_id
    _pipeline_done = done_event


@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """Return TwiML that starts a Media Stream."""
    host = request.headers.get("host", "localhost:8765")
    ws_url = f"wss://{host}/twilio/media-stream"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="callId" value="{_call_id or ''}" />
        </Stream>
    </Connect>
</Response>"""

    log.info("twiml_response", ws_url=ws_url)
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/twilio/media-stream")
async def twilio_media_stream(ws: WebSocket):
    """Handle bidirectional audio via Twilio Media Streams."""
    await ws.accept()
    log.info("media_stream_connected")

    stream_sid = None

    try:
        # Wait for the "start" event to get stream SID
        while True:
            data = await ws.receive_text()
            message = json.loads(data)
            if message.get("event") == "start":
                stream_sid = message["start"]["streamSid"]
                log.info("media_stream_started", stream_sid=stream_sid)
                break

        # Wire up the telephony provider with this WebSocket
        _telephony.set_websocket(ws, stream_sid)

        # Run pipeline in background
        pipeline_task = asyncio.create_task(
            _pipeline.run(_call_context, _call_id)
        )

        # Forward incoming Twilio messages to the telephony provider
        # Also check if pipeline has ended (call complete)
        try:
            while True:
                try:
                    data = await asyncio.wait_for(ws.receive_text(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Check if pipeline ended while we were waiting
                    if pipeline_task.done():
                        break
                    continue
                message = json.loads(data)
                await _telephony.handle_media_message(message)
                if message.get("event") == "stop":
                    break
        except Exception:
            pass  # WebSocket closed

        # Wait for pipeline to finish
        if not pipeline_task.done():
            pipeline_task.cancel()
            try:
                await pipeline_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        log.error("media_stream_error", error=str(e))
    finally:
        log.info("media_stream_disconnected")
        if _pipeline_done:
            _pipeline_done.set()

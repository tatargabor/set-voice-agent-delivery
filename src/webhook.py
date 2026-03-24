"""FastAPI webhook server for Twilio call control and Media Streams."""

import asyncio
import base64
import json
import os
import threading
from datetime import datetime
import structlog
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .agent import ConversationAgent, CallContext
from .caller_lookup import lookup_caller
from .metrics import CallMetrics, mask_phone
from .pipeline import CallPipeline
from .response_layers import ResponseLayers
from .providers.soniox_stt import SonioxSTTProvider
from .providers.google_tts import GoogleTTSProvider
from .providers.twilio_provider import TwilioTelephonyProvider

log = structlog.get_logger()

app = FastAPI()

# CORS for browser widget embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Serve static files (voice widget)
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# --- Outbound mode: pre-configured state (set by call_runner) ---
_outbound_context: CallContext | None = None
_outbound_pipeline: CallPipeline | None = None
_outbound_telephony: TwilioTelephonyProvider | None = None
_outbound_call_id: str | None = None
_outbound_done: threading.Event | None = None

# --- Inbound mode: state ---
_inbound_mode: bool = False
_inbound_busy: bool = False
_inbound_done: threading.Event | None = None


def configure_outbound(
    ctx: CallContext,
    pipeline: CallPipeline,
    telephony: TwilioTelephonyProvider,
    call_id: str,
    done_event: threading.Event,
) -> None:
    """Configure for outbound call (called by call_runner)."""
    global _outbound_context, _outbound_pipeline, _outbound_telephony, _outbound_call_id, _outbound_done
    _outbound_context = ctx
    _outbound_pipeline = pipeline
    _outbound_telephony = telephony
    _outbound_call_id = call_id
    _outbound_done = done_event


# Keep backward compat
configure = configure_outbound


def enable_inbound_mode(done_event: threading.Event | None = None) -> None:
    """Enable inbound call handling."""
    global _inbound_mode, _inbound_done
    _inbound_mode = True
    _inbound_done = done_event


@app.get("/twilio/token")
async def twilio_token(request: Request, identity: str = "browser-user"):
    """Generate Twilio Access Token for browser voice client."""
    from twilio.jwt.access_token import AccessToken
    from twilio.jwt.access_token.grants import VoiceGrant

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    api_key_sid = os.environ.get("TWILIO_API_KEY_SID", "")
    api_key_secret = os.environ.get("TWILIO_API_KEY_SECRET", "")
    twiml_app_sid = os.environ.get("TWILIO_TWIML_APP_SID", "")

    if not all([account_sid, api_key_sid, api_key_secret, twiml_app_sid]):
        return JSONResponse(
            {"error": "Twilio browser client not configured. Run: python -m src.twilio_setup"},
            status_code=500,
        )

    token = AccessToken(account_sid, api_key_sid, api_key_secret, identity=identity, ttl=3600)
    voice_grant = VoiceGrant(outgoing_application_sid=twiml_app_sid)
    token.add_grant(voice_grant)

    log.info("token_generated", identity=identity)
    return JSONResponse({"token": token.to_jwt()})


@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """Return TwiML that starts a Media Stream, or reject if busy."""
    global _inbound_busy

    host = request.headers.get("host", "localhost:8765")
    ws_url = f"wss://{host}/twilio/media-stream"

    if _inbound_mode and _inbound_busy:
        # Reject concurrent calls
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hu-HU">Jelenleg foglalt vagyok, kérem hívjon később.</Say>
    <Hangup/>
</Response>"""
        log.info("call_rejected_busy")
        return Response(content=twiml, media_type="application/xml")

    if _inbound_mode:
        # Extract caller info from Twilio POST data
        form = await request.form()
        caller_phone = form.get("From", "")
        call_sid = form.get("CallSid", "")
        log.info("inbound_call", caller=caller_phone, call_sid=call_sid)

        # Store for the WebSocket handler
        app.state.pending_inbound = {
            "caller_phone": caller_phone,
            "call_sid": call_sid,
        }

    call_id = ""
    if _outbound_call_id:
        call_id = _outbound_call_id
    elif hasattr(app.state, "pending_inbound"):
        call_id = app.state.pending_inbound.get("call_sid", "")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="callId" value="{call_id}" />
        </Stream>
    </Connect>
</Response>"""

    log.info("twiml_response", ws_url=ws_url)
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/twilio/media-stream")
async def twilio_media_stream(ws: WebSocket):
    """Handle bidirectional audio via Twilio Media Streams."""
    global _inbound_busy

    await ws.accept()
    log.info("media_stream_connected")

    # Determine mode and get the right objects
    if _inbound_mode and hasattr(app.state, "pending_inbound"):
        inbound_info = app.state.pending_inbound
        _inbound_busy = True

        # Build context from caller lookup
        caller_phone = inbound_info["caller_phone"]
        call_sid = inbound_info["call_sid"]
        customer = lookup_caller(caller_phone)

        ctx = CallContext(
            customer_name=customer.get("customer_name", ""),
            company_name=customer.get("company_name", "WebBuilder Kft."),
            purpose=f"Bejövő hívás — {customer.get('customer_name', 'ismeretlen')} kérdése",
            website_url=customer.get("website_url"),
        )

        telephony = TwilioTelephonyProvider()
        stt = SonioxSTTProvider()
        tts = GoogleTTSProvider()
        agent = ConversationAgent()

        metrics = CallMetrics(
            call_id=call_sid,
            timestamp_start=datetime.now(),
            customer_name=customer.get("customer_name", "ismeretlen"),
            script_name=customer.get("script", "inbound"),
            phone_masked=mask_phone(caller_phone),
        )

        pipeline = CallPipeline(stt=stt, tts=tts, telephony=telephony, agent=agent, metrics=metrics)
        pipeline.response_layers = ResponseLayers()
        done_event = _inbound_done
    else:
        # Outbound mode — use pre-configured state
        ctx = _outbound_context
        telephony = _outbound_telephony
        pipeline = _outbound_pipeline
        call_sid = _outbound_call_id or ""
        done_event = _outbound_done

    stream_sid = None

    try:
        # Wait for the "start" event to get stream SID
        while True:
            data = await ws.receive_text()
            message = json.loads(data)
            if message.get("event") == "start":
                stream_sid = message["start"]["streamSid"]
                call_sid_from_start = message["start"].get("callSid", call_sid)
                log.info("media_stream_started", stream_sid=stream_sid, call_sid=call_sid_from_start)
                break

        # Wire up the telephony provider with this WebSocket
        telephony.set_websocket(ws, stream_sid)

        # Run pipeline in background
        pipeline_task = asyncio.create_task(
            pipeline.run(ctx, call_sid)
        )

        # Forward incoming Twilio messages to the telephony provider
        try:
            while True:
                try:
                    data = await asyncio.wait_for(ws.receive_text(), timeout=1.0)
                except asyncio.TimeoutError:
                    if pipeline_task.done():
                        break
                    continue
                message = json.loads(data)
                await telephony.handle_media_message(message)
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
        if _inbound_mode:
            _inbound_busy = False
            # Log the inbound call
            if _inbound_mode and hasattr(pipeline, 'metrics') and pipeline.metrics:
                from .logger import CallLogger
                call_logger = CallLogger()
                call_logger.save(pipeline.metrics, ctx.history, outcome="completed")
                log.info("inbound_call_logged")
        if done_event:
            done_event.set()

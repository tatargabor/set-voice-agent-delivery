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

from .config import get_settings
from .agent import ConversationAgent, CallContext
from .caller_lookup import lookup_caller
from .i18n import (
    _DEFAULT_PURPOSE_OUTBOUND, _DEFAULT_PURPOSE_INBOUND, _UNKNOWN_CUSTOMER,
    _PROJECT_LABEL, get_text,
)
from .metrics import CallMetrics, mask_phone
from .pipeline import CallPipeline
from .project_context import load_project_context
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


def _resolve_project_dir(project_id: str) -> str | None:
    """Resolve project name to directory path via set-project list."""
    import subprocess
    try:
        result = subprocess.run(
            ["set-project", "list"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if " -> " in line and not line.strip().startswith("└"):
                parts = line.strip().split(" -> ", 1)
                if parts[0].strip() == project_id:
                    return parts[1].strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    # Fallback: try projects_dir/name
    fallback = Path(get_settings().projects_dir) / project_id
    return str(fallback) if fallback.exists() else None


@app.get("/api/config")
async def get_config():
    """Return language and company name for the voice widget UI."""
    settings = get_settings()
    return {"language": settings.language, "company_name": settings.company_name}


@app.get("/api/projects")
async def list_projects():
    """Discover projects from set-project list (registered projects)."""
    import subprocess
    projects = []
    try:
        result = subprocess.run(
            ["set-project", "list"], capture_output=True, text=True, timeout=5
        )
        # Parse "    name -> /path" lines (top-level projects, not worktrees)
        for line in result.stdout.splitlines():
            line = line.rstrip()
            if " -> " in line and not line.strip().startswith("└"):
                parts = line.strip().split(" -> ", 1)
                name = parts[0].strip()
                path = parts[1].strip()
                projects.append({"id": name, "label": name, "path": path})
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback: scan projects_dir
        code_dir = Path(get_settings().projects_dir)
        if code_dir.exists():
            for d in sorted(code_dir.iterdir()):
                if d.is_dir() and not d.name.startswith("."):
                    is_project = any((d / f).exists() for f in ["pyproject.toml", "package.json", "openspec", ".git"])
                    if is_project:
                        projects.append({"id": d.name, "label": d.name, "path": str(d)})
    return JSONResponse({"projects": projects})


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


@app.post("/api/call")
async def api_call(request: Request):
    """Initiate outbound phone call from widget."""
    data = await request.json()
    phone = data.get("phone", "")
    project_id = data.get("project", "")
    identity = data.get("identity", "")

    if not phone:
        return JSONResponse({"error": "Phone number required"}, status_code=400)

    host = request.headers.get("host", "localhost:8765")
    public_url = f"https://{host}"

    # Store call info for the media stream handler
    app.state.pending_inbound = {
        "caller_phone": phone,
        "call_sid": "",  # Will be updated after call creation
        "project_id": project_id,
        "outbound_phone": phone,
    }

    try:
        from twilio.rest import Client
        client = Client()
        call = client.calls.create(
            to=phone,
            from_=os.environ.get("TWILIO_PHONE_NUMBER", ""),
            url=f"{public_url}/twilio/voice-outbound",
        )
        app.state.pending_inbound["call_sid"] = call.sid
        log.info("api_call_initiated", phone=phone, call_sid=call.sid, project=project_id)
        return JSONResponse({"status": "calling", "call_sid": call.sid})
    except Exception as e:
        log.error("api_call_error", error=str(e))
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/index-project")
async def api_index_project(request: Request):
    """Trigger project index generation (called by widget on project select)."""
    data = await request.json()
    project_id = data.get("project", "")

    if not project_id:
        return JSONResponse({"error": "project required"}, status_code=400)

    project_dir = _resolve_project_dir(project_id)
    if not project_dir or not Path(project_dir).exists():
        return JSONResponse({"error": f"Project not found: {project_id}"}, status_code=404)

    from .project_indexer import read_cache, generate_index

    # Check if cache is fresh
    cached = read_cache(project_id, Path(project_dir))
    if cached:
        return JSONResponse({"status": "cached", "project": project_id})

    # Generate in background
    import asyncio
    asyncio.create_task(generate_index(project_dir, project_id))
    return JSONResponse({"status": "indexing", "project": project_id}, status_code=202)


@app.post("/twilio/voice-outbound")
async def twilio_voice_outbound(request: Request):
    """TwiML for outbound calls initiated from the widget."""
    host = request.headers.get("host", "localhost:8765")
    ws_url = f"wss://{host}/twilio/media-stream"
    call_id = ""
    if hasattr(app.state, "pending_inbound"):
        call_id = app.state.pending_inbound.get("call_sid", "")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="callId" value="{call_id}" />
        </Stream>
    </Connect>
</Response>"""
    log.info("outbound_twiml", ws_url=ws_url, call_id=call_id)
    return Response(content=twiml, media_type="application/xml")


@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """Return TwiML that starts a Media Stream, or reject if busy."""
    global _inbound_busy

    host = request.headers.get("host", "localhost:8765")
    ws_url = f"wss://{host}/twilio/media-stream"

    if _inbound_mode and _inbound_busy:
        # Reject concurrent calls
        from .i18n import _BUSY_MESSAGE, _BUSY_LANGUAGE, get_text
        busy_msg = get_text(_BUSY_MESSAGE)
        busy_lang = get_text(_BUSY_LANGUAGE)
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{busy_lang}">{busy_msg}</Say>
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

        # Get project and phone from custom params (sent by browser widget)
        project_id = form.get("project", "") or form.get("Project", "")
        outbound_phone = form.get("phone", "")

        # Store for the WebSocket handler
        app.state.pending_inbound = {
            "caller_phone": caller_phone,
            "call_sid": call_sid,
            "project_id": project_id,
            "outbound_phone": outbound_phone,
        }

        pass  # outbound_phone handled via /api/call REST endpoint

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

        # Load project context — from widget selection or contacts.yaml
        project_context_str = ""
        project_id = inbound_info.get("project_id", "")
        project_dir = _resolve_project_dir(project_id) if project_id else customer.get("project_dir")
        if project_dir and Path(project_dir).exists():
            pc = load_project_context(project_dir, customer.get("customer_name", ""))
            project_context_str = pc.to_prompt_section()
            # Prepend project name so the agent knows which project is selected
            if project_id:
                label = get_text(_PROJECT_LABEL)
                project_context_str = f"{label}: {project_id}\n\n{project_context_str}"
            log.info("project_context_loaded", project=project_id, chars=len(project_context_str))

        outbound_phone = inbound_info.get("outbound_phone", "")
        is_outbound = bool(outbound_phone)

        ctx = CallContext(
            customer_name=customer.get("customer_name", ""),
            company_name=customer.get("company_name", get_settings().company_name),
            purpose=customer.get("purpose", get_text(_DEFAULT_PURPOSE_OUTBOUND)) if is_outbound else get_text(_DEFAULT_PURPOSE_INBOUND).format(name=customer.get("customer_name", get_text(_UNKNOWN_CUSTOMER))),
            website_url=customer.get("website_url"),
            project_context=project_context_str,
            project_dir=project_dir,
            call_direction="outbound" if is_outbound else "inbound",
        )

        telephony = TwilioTelephonyProvider()
        stt = SonioxSTTProvider()
        tts = GoogleTTSProvider()
        agent = ConversationAgent()

        metrics = CallMetrics(
            call_id=call_sid,
            timestamp_start=datetime.now(),
            customer_name=customer.get("customer_name", get_text(_UNKNOWN_CUSTOMER)),
            script_name=customer.get("script", "inbound"),
            phone_masked=mask_phone(caller_phone),
            research_mode=get_settings().research.mode,
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
            if pipeline and hasattr(pipeline, 'metrics') and pipeline.metrics:
                from .logger import CallLogger
                call_logger = CallLogger()
                call_logger.save(pipeline.metrics, ctx.history, outcome="completed")
                log.info("inbound_call_logged")

                # Generate post-call summary for dev team
                try:
                    from .call_summary import generate_call_summary
                    project_id = inbound_info.get("project_id", "") if inbound_info else ""
                    summary = await generate_call_summary(
                        transcript=ctx.history,
                        customer_name=ctx.customer_name,
                        project_id=project_id,
                        call_id=pipeline.metrics.call_id,
                    )
                    if summary.get("modification_requests"):
                        log.info("dev_action_items",
                                 project=project_id,
                                 items=summary["modification_requests"])
                except Exception as e:
                    log.error("summary_generation_failed", error=str(e))
        if done_event:
            done_event.set()

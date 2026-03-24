"""Twilio telephony provider — outbound calls + Media Streams audio."""

import asyncio
import base64
import json
import os
import threading
import structlog
from typing import AsyncIterator

from twilio.rest import Client as TwilioClient

from .base import TelephonyProvider

log = structlog.get_logger()

# Timeout waiting for Twilio mark confirmation
_MARK_TIMEOUT_SEC = 5.0


class TwilioTelephonyProvider(TelephonyProvider):
    """Telephony via Twilio REST API and Media Streams WebSocket."""

    def __init__(self):
        account_sid = os.environ["TWILIO_ACCOUNT_SID"]
        auth_token = os.environ["TWILIO_AUTH_TOKEN"]
        self._from_number = os.environ["TWILIO_PHONE_NUMBER"]
        self._client = TwilioClient(account_sid, auth_token)
        # WebSocket connection set externally by the webhook server
        self._ws = None
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._stream_sid: str | None = None
        # Mark event tracking
        self._mark_events: dict[str, threading.Event] = {}
        self._mark_counter: int = 0

    async def place_call(self, phone_number: str, webhook_url: str) -> str:
        """Place an outbound call via Twilio REST API."""
        call = self._client.calls.create(
            to=phone_number,
            from_=self._from_number,
            url=webhook_url,
        )
        return call.sid

    async def hangup(self, call_id: str) -> None:
        """Terminate an active call."""
        self._client.calls(call_id).update(status="completed")

    def set_websocket(self, ws, stream_sid: str) -> None:
        """Set the Media Streams WebSocket connection."""
        self._ws = ws
        self._stream_sid = stream_sid

    async def handle_media_message(self, message: dict) -> None:
        """Process an incoming Media Streams message."""
        event = message.get("event")
        if event == "media":
            payload = message["media"]["payload"]
            audio_bytes = base64.b64decode(payload)
            await self._audio_queue.put(audio_bytes)
        elif event == "mark":
            name = message.get("mark", {}).get("name", "")
            if name in self._mark_events:
                self._mark_events.pop(name).set()
                log.debug("mark_received", name=name)
        elif event == "stop":
            await self._audio_queue.put(None)

    async def get_audio_stream(self, call_id: str) -> AsyncIterator[bytes]:
        """Yield raw mulaw audio bytes from the inbound Media Stream."""
        while True:
            chunk = await self._audio_queue.get()
            if chunk is None:
                break
            yield chunk

    async def send_audio(self, call_id: str, audio: bytes) -> None:
        """Send audio bytes to the active call via Media Streams WebSocket."""
        if self._ws is None:
            raise RuntimeError("No WebSocket connection. Wait for Twilio to connect.")

        payload = base64.b64encode(audio).decode("ascii")
        message = json.dumps({
            "event": "media",
            "streamSid": self._stream_sid,
            "media": {"payload": payload},
        })
        await self._ws.send_text(message)
        log.debug("audio_sent", bytes=len(audio))

    async def send_mark(self, call_id: str) -> None:
        """Send a mark and wait for Twilio to confirm playback completion.

        Blocks until Twilio sends back the mark event (meaning all audio
        before this mark has been played to the caller), or times out.
        Uses threading.Event because mark confirmation arrives in a different
        thread (uvicorn) than the pipeline awaiting it.
        """
        if self._ws is None:
            return

        self._mark_counter += 1
        name = f"mark-{self._mark_counter}"

        evt = threading.Event()
        self._mark_events[name] = evt

        message = json.dumps({
            "event": "mark",
            "streamSid": self._stream_sid,
            "mark": {"name": name},
        })
        await self._ws.send_text(message)

        # Wait in executor to not block the event loop
        loop = asyncio.get_event_loop()
        confirmed = await loop.run_in_executor(None, evt.wait, _MARK_TIMEOUT_SEC)

        if confirmed:
            log.debug("mark_confirmed", name=name)
        else:
            self._mark_events.pop(name, None)
            log.warning("mark_timeout", name=name, timeout=_MARK_TIMEOUT_SEC)

    async def clear_audio(self, call_id: str) -> None:
        """Clear Twilio's audio buffer immediately (for barge-in)."""
        if self._ws is None:
            return

        message = json.dumps({
            "event": "clear",
            "streamSid": self._stream_sid,
        })
        await self._ws.send_text(message)
        log.debug("audio_cleared")

"""Twilio telephony provider — outbound calls + Media Streams audio."""

import asyncio
import base64
import json
import os
from typing import AsyncIterator

from twilio.rest import Client as TwilioClient

from .base import TelephonyProvider


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

    async def place_call(self, phone_number: str, webhook_url: str) -> str:
        """Place an outbound call via Twilio REST API.

        Args:
            phone_number: The number to call (E.164 format).
            webhook_url: URL Twilio will POST to when the call connects.

        Returns:
            The Twilio Call SID.
        """
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
        """Set the Media Streams WebSocket connection.

        Called by the webhook server when Twilio connects.
        """
        self._ws = ws
        self._stream_sid = stream_sid

    async def handle_media_message(self, message: dict) -> None:
        """Process an incoming Media Streams message.

        Called by the webhook server for each WebSocket message from Twilio.
        """
        event = message.get("event")
        if event == "media":
            payload = message["media"]["payload"]
            audio_bytes = base64.b64decode(payload)
            await self._audio_queue.put(audio_bytes)
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

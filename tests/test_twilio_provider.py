"""Integration test for Twilio provider (requires TWILIO credentials)."""

import pytest
from src.providers.twilio_provider import TwilioTelephonyProvider


@pytest.mark.telephony
async def test_place_and_hangup():
    """Place a call and immediately hang up (verifies credentials work)."""
    provider = TwilioTelephonyProvider()

    # Use a dummy webhook URL — the call will connect but won't get TwiML
    # We hang up immediately so it doesn't ring long
    call_sid = await provider.place_call(
        phone_number="+36203911669",  # verified number from env
        webhook_url="https://handler.twilio.com/twiml/dummy",
    )
    assert call_sid.startswith("CA"), f"Expected Call SID starting with CA, got: {call_sid}"

    # Immediately hang up
    await provider.hangup(call_sid)

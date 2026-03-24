## Why

Phone-based testing costs ~$0.085/min outbound, and Hungarian inbound numbers aren't available on Twilio. A browser-based voice client costs ~$0.004/min, needs no phone number, and doubles as the **production delivery method** — customers click a button on their website to talk to the AI agent. The existing pipeline (STT→Claude→TTS) works unchanged; Twilio treats browser calls identically to phone calls.

## What Changes

- Create Twilio Access Token endpoint (`GET /twilio/token`) for browser authentication
- Create a minimal HTML test page with `@twilio/voice-sdk` — microphone button → connects to voice agent
- Create an embeddable widget version for customer websites
- Handle `client:*` caller identity in webhook (browser calls don't have a phone number)
- One-time Twilio setup: TwiML App + API Key (scripted or documented)

## Capabilities

### New Capabilities
- `browser-voice`: Browser-based voice client using Twilio Client SDK (WebRTC) — works as test tool and production widget
- `twilio-token`: Access Token generation endpoint for browser authentication

### Modified Capabilities

## Impact

- **Code**: new endpoint in `src/webhook.py`, new `static/voice-widget.html`, new `static/voice-widget.js`
- **Config**: 3 new env vars: `TWILIO_API_KEY_SID`, `TWILIO_API_KEY_SECRET`, `TWILIO_TWIML_APP_SID`
- **Dependencies**: none server-side (Twilio JS SDK loaded via CDN in browser)
- **Twilio setup**: create TwiML App + API Key (one-time, can be scripted)

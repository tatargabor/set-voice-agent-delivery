## 1. Twilio Setup

- [ ] 1.1 Create `src/twilio_setup.py` — script that creates TwiML App + API Key via Twilio API, prints env vars
- [ ] 1.2 Run setup, add `TWILIO_API_KEY_SID`, `TWILIO_API_KEY_SECRET`, `TWILIO_TWIML_APP_SID` to `.env`
- [ ] 1.3 Update `.env.example` with the new vars

## 2. Token Endpoint

- [ ] 2.1 Add `GET /twilio/token` endpoint to `webhook.py` — generate Access Token with VoiceGrant
- [ ] 2.2 Accept optional `identity` query param for caller identification
- [ ] 2.3 Add test: GET /twilio/token returns valid JSON with token field

## 3. Browser Widget

- [ ] 3.1 Create `static/` directory, add `voice-widget.html` — call button, status display, hangup
- [ ] 3.2 Create `static/voice-widget.js` — fetch token, init Twilio.Device, connect/disconnect logic
- [ ] 3.3 Mount `/static` in FastAPI for serving the widget
- [ ] 3.4 Make it mobile-friendly (responsive, large touch targets)

## 4. Webhook Updates

- [ ] 4.1 Update `caller_lookup.py` to handle `client:*` identities — extract name, look up in contacts
- [ ] 4.2 Update webhook inbound handler for browser caller identity
- [ ] 4.3 Add test: lookup_caller with "client:gabor" returns customer data

## 5. Integration Test

- [ ] 5.1 Start inbound server, open voice-widget.html in browser, verify call connects and pipeline runs

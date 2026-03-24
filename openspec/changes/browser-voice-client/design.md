## Context

Twilio Client JS SDK (`@twilio/voice-sdk`) turns the browser into a VoIP endpoint via WebRTC. From Twilio's perspective, a browser call is identical to a phone call — it hits the same TwiML webhook, gets the same `<Connect><Stream>` response, opens the same Media Streams WebSocket. Our entire pipeline works without modification.

The flow:
```
Browser                    Twilio                     Our Server
  │                          │                            │
  │  1. GET /twilio/token    │                            │
  │─────────────────────────────────────────────────────>│
  │<─────────────────────────────────────────────────────│
  │     Access Token (JWT)   │                            │
  │                          │                            │
  │  2. device.connect()     │                            │
  │  (WebRTC)               │                            │
  │─────────────────────────>│                            │
  │                          │ 3. POST /twilio/voice      │ ← SAME endpoint
  │                          │───────────────────────────>│
  │                          │  4. TwiML: <Stream>        │ ← SAME response
  │                          │<───────────────────────────│
  │                          │ 5. WS /twilio/media-stream │ ← SAME handler
  │                          │───────────────────────────>│
  │                          │                            │
  │  6. Bidirectional audio  │  Media Streams WS          │
  │<────────────────────────>│<──────────────────────────>│
```

## Goals / Non-Goals

**Goals:**
- Browser-to-agent voice calls using existing pipeline (zero pipeline changes)
- Test page for development (localhost)
- Embeddable widget for customer websites (production)
- Mobile-friendly (works on phone browsers too)

**Non-Goals:**
- Video calls
- Chat/text mode (voice only)
- Custom UI framework (plain HTML/JS, can be styled later)

## Decisions

### 1. Twilio setup (one-time)

Three resources needed:
- **TwiML App**: points Voice URL to our `/twilio/voice` endpoint
- **API Key**: generates `API_KEY_SID` + `API_KEY_SECRET` for signing tokens
- Both can be created via Twilio API (scripted in a setup command)

### 2. Token endpoint

New endpoint: `GET /twilio/token?identity=<optional-name>`

Returns JSON: `{"token": "eyJ..."}`

Token contains:
- `VoiceGrant` with `outgoing_application_sid` (the TwiML App)
- Identity: browser user name (for caller lookup)
- TTL: 3600 seconds (1 hour)

### 3. HTML widget

Minimal HTML page served from `/static/voice-widget.html`:

```html
<button id="call-btn">🎤 Beszéljen az AI asszisztenssel</button>
<div id="status">Kapcsolódás...</div>
<script src="https://sdk.twilio.com/js/client/releases/2.5/twilio.min.js"></script>
<script src="/static/voice-widget.js"></script>
```

The JS:
1. Fetches token from `/twilio/token`
2. Creates `Twilio.Device`
3. On button click: `device.connect()` → pipeline runs
4. Shows status: connecting → speaking → ended

### 4. Caller identity for browser calls

Browser calls have `From: client:<identity>` instead of a phone number. Update `lookup_caller()` to handle this:
- `client:gabor` → look up by identity name
- `client:unknown` → use default

### 5. File structure

```
src/
├── webhook.py          # + GET /twilio/token endpoint
static/
├── voice-widget.html   # test page + embeddable widget
├── voice-widget.js     # Twilio Client SDK logic
```

## Risks / Trade-offs

- **[Risk] CORS for widget embedding** → Mitigation: FastAPI CORS middleware for the token endpoint
- **[Risk] Token security** → Mitigation: short TTL (1h), optional identity validation
- **[Trade-off] CDN-loaded Twilio JS vs npm bundle** → CDN is simpler for a widget, no build step needed

## Context

The outbound call system starts a webhook server per call, places the call, runs the pipeline, then shuts down. For inbound, the server must run **permanently** — any call can arrive at any time. The Twilio number (+36203911669) is already set up; we just need to configure its incoming call webhook URL.

## Goals / Non-Goals

**Goals:**
- Persistent webhook server accepting incoming calls
- Caller identification from phone number → customer data
- Reuse existing CallPipeline, metrics, logging
- Simple CLI: `python -m src.inbound_server`

**Non-Goals:**
- IVR menu / call routing (direct to agent)
- Multiple simultaneous calls (one at a time for MVP)
- Outbound call removal (both modes coexist)

## Decisions

### 1. Contacts file for caller lookup

```yaml
# contacts.yaml
contacts:
  "+36301234567":
    customer_name: "Kovács János"
    company_name: "WebBuilder Kft."
    script: "website_followup"
    website_url: "https://kovacs-janos.hu"
    project_dir: "/home/tg/code2/kovacs-project"  # optional, for future context loading

  "+36309876543":
    customer_name: "Nagy Anna"
    company_name: "WebBuilder Kft."
    script: "website_followup"
    website_url: "https://nagy-anna.hu"

# Unknown callers get a generic greeting
default:
  company_name: "WebBuilder Kft."
  script: "website_followup"
```

### 2. Inbound webhook flow

```
Ügyfél hív +36203911669
       │
       ▼
Twilio POST /twilio/voice
       │
       ├── Lookup caller phone in contacts.yaml
       │   ├── Found → load customer context
       │   └── Not found → use default context, ask for name
       │
       ▼
TwiML: <Connect><Stream> → Media Stream WebSocket
       │
       ▼
Pipeline runs (same as outbound)
       │
       ▼
Hangup + log
```

### 3. Server architecture

The `inbound_server.py` is simpler than `call_runner.py`:
- Starts uvicorn permanently (not in a background thread)
- No call placement logic
- Webhook creates pipeline per incoming call
- Supports one call at a time (queue or reject concurrent calls)

### 4. Twilio number configuration

The Twilio number's incoming webhook must point to our server:
```
https://<ngrok-url>/twilio/voice
```
This is configured in Twilio Console → Phone Numbers → the number → Voice Configuration → "A Call Comes In" → Webhook URL.

Or via API: `client.incoming_phone_numbers(sid).update(voice_url=...)`

### 5. Modified webhook.py

Currently webhook.py uses global state (`_pipeline`, `_call_context`). For inbound, these are created **per call** inside the webhook handler:

```python
@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    # Get caller phone from Twilio POST data
    form = await request.form()
    caller = form.get("From")

    # Lookup customer
    customer = lookup_caller(caller)

    # Create pipeline for this call
    ctx = CallContext(...)
    pipeline = CallPipeline(...)

    # Return TwiML with Media Stream
```

## Risks / Trade-offs

- **[Risk] Server must be always-on** → Mitigation: for dev, ngrok + local server. For production, deploy to cloud.
- **[Risk] Concurrent calls** → Mitigation: MVP handles one call at a time. Reject or queue additional calls.
- **[Trade-off] contacts.yaml vs database** → Simple file for MVP, same as DNC list approach. Scalable later.

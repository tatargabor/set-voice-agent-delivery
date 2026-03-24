## Why

Outbound calls to Hungarian numbers cost ~$0.085/min ($0.126 for an 88 sec call). Inbound calls cost ~$0.0085/min — **10x cheaper**. Many use cases work better as inbound: the customer calls when convenient, no DNC/legal hours concerns, and it feels less intrusive. The existing pipeline (STT→Claude→TTS) is reusable — we just need a persistent webhook server and inbound call handling.

## What Changes

- Create a persistent inbound server mode: webhook server runs continuously, waiting for incoming calls
- Handle inbound call flow: Twilio calls webhook → Media Stream connects → pipeline runs → hangup
- Match incoming caller to a customer/project based on phone number (simple lookup table)
- Reuse existing CallPipeline, CallMetrics, CallLogger — no changes needed there
- Add CLI mode: `python -m src.inbound_server --port 8765`

## Capabilities

### New Capabilities
- `inbound-call`: Accept incoming calls on the Twilio number, match caller to customer/project, run the voice agent pipeline
- `caller-lookup`: Map incoming phone numbers to customer names and project contexts

### Modified Capabilities

## Impact

- **Code**: new `src/inbound_server.py` (persistent server), new `src/caller_lookup.py` (phone→customer mapping), modify `src/webhook.py` (handle inbound without pre-configured context)
- **Config**: new `contacts.yaml` file mapping phone numbers to customer data
- **No new dependencies** — same FastAPI/uvicorn stack
- **Infrastructure**: server must run persistently (not just during a call), ngrok must stay up

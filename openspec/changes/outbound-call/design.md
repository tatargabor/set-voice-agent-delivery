## Context

After Change 2, the `CallPipeline` can run a conversation over audio. But there's no way to start a call — no webhook server for Twilio, no call script loading, no safety checks. This change is the "last mile" that makes the system callable from the command line.

```
CLI Command
    │
    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Load Script │───▶│ Safety Check│───▶│ Place Call  │
│ (YAML)      │    │ (DNC+hours) │    │ (Twilio)    │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
                                    ┌─────────────┐
                                    │ Webhook     │◀── Twilio connects
                                    │ Server      │    via WebSocket
                                    │ (FastAPI)   │
                                    └──────┬──────┘
                                           │
                                           ▼
                                    ┌─────────────┐
                                    │ CallPipeline│
                                    │ (Change 2)  │
                                    └─────────────┘
```

## Goals / Non-Goals

**Goals:**
- Load call scripts from YAML into CallContext
- Enforce safety rules before every call (DNC list, legal hours)
- Run FastAPI webhook server for Twilio call events and Media Streams
- Provide CLI entry point: `python -m src.call_runner --script website_followup --phone +36...`
- End-to-end Level 2 tests

**Non-Goals:**
- Web UI or dashboard
- Batch calling (multiple calls in sequence/parallel)
- Call recording storage
- CRM integration

## Decisions

### 1. Call script loader

Parse `call_scripts/*.yaml` into `CallContext`. The YAML already has the right structure (`website_followup.yaml`). Validate required fields, substitute variables (customer_name, company_name, website_url) from CLI args or a contacts file.

### 2. Safety module

```python
# src/safety.py
class CallSafety:
    def check_dnc(phone: str) -> bool       # check against local DNC file
    def add_to_dnc(phone: str) -> None       # add number after "ne hívjatok"
    def check_legal_hours() -> bool          # 08:00-20:00 local time
    def pre_call_check(phone: str) -> None   # raises if any check fails
```

DNC list: simple text file (`data/dnc.txt`), one number per line. No database needed for MVP.

### 3. FastAPI webhook server

Two endpoints:
- `POST /twilio/voice` — TwiML response that starts Media Stream
- `WS /twilio/media-stream` — WebSocket endpoint for bidirectional audio

The server starts before the call is placed, and the Twilio call's webhook URL points to it. For development, use ngrok to expose the local server.

### 4. CLI entry point

```bash
python -m src.call_runner \
  --script website_followup \
  --phone "+36301234567" \
  --customer-name "Kovács János" \
  --company-name "WebBuilder Kft." \
  --website-url "https://kovacs-janos.hu"
```

Flow: parse args → load script → safety checks → start webhook server → place call → run pipeline → hangup → print transcript.

### 5. File structure

```
src/
├── call_runner.py       # CLI entry point, main orchestration
├── webhook.py           # FastAPI app with Twilio endpoints
├── safety.py            # DNC list, legal hours checks
├── script_loader.py     # YAML call script → CallContext
data/
├── dnc.txt              # Do Not Call list (gitignored)
```

## Risks / Trade-offs

- **[Risk] Webhook URL must be publicly accessible** → Mitigation: document ngrok setup for development, production deployment uses proper domain
- **[Risk] FastAPI adds dependency weight** → Mitigation: it's lightweight and we'll need HTTP server anyway for production
- **[Trade-off] Local DNC file vs database** → Simple for MVP, but won't scale to multi-instance. Acceptable for now, can migrate to SQLite/Postgres later
- **[Risk] Twilio trial account limitations** → Mitigation: document that trial accounts can only call verified numbers, test with own phone

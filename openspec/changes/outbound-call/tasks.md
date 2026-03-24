## 1. Call Script Loader

- [ ] 1.1 Create `src/script_loader.py` — parse YAML call scripts, validate required fields, substitute variables
- [ ] 1.2 Add test: load `website_followup.yaml` with variables → verify CallContext output
- [ ] 1.3 Add test: missing required field → verify validation error

## 2. Safety Module

- [ ] 2.1 Create `src/safety.py` — `CallSafety` class with `check_dnc()`, `add_to_dnc()`, `check_legal_hours()`, `pre_call_check()`
- [ ] 2.2 Create `data/` directory, add `data/dnc.txt` placeholder (gitignored)
- [ ] 2.3 Add test: number on DNC list → blocked
- [ ] 2.4 Add test: call at 06:30 → blocked, call at 14:00 → allowed
- [ ] 2.5 Add test: add_to_dnc writes number to file

## 3. Webhook Server

- [ ] 3.1 Add `fastapi` and `uvicorn` to pyproject.toml dependencies
- [ ] 3.2 Create `src/webhook.py` — FastAPI app with `POST /twilio/voice` returning TwiML with Media Stream connect
- [ ] 3.3 Add WebSocket endpoint `WS /twilio/media-stream` — decode inbound audio, encode outbound audio, bridge to CallPipeline
- [ ] 3.4 Add test: POST /twilio/voice → verify TwiML response structure

## 4. Call Runner

- [ ] 4.1 Create `src/call_runner.py` — CLI entry point with argparse (--script, --phone, --customer-name, --company-name, --website-url)
- [ ] 4.2 Wire the full flow: load script → safety check → start uvicorn → place call → run pipeline → hangup
- [ ] 4.3 Add GDPR recording notice to greeting flow
- [ ] 4.4 Add transcript output at end of call
- [ ] 4.5 Add DNC detection during call — if customer says "ne hívjatok", add to DNC list

## 5. Integration

- [ ] 5.1 Add Level 2 integration test: full outbound call to verified number (requires all credentials)
- [ ] 5.2 Document ngrok setup for local development in README or comments

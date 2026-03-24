## Why

The pipeline (Change 2) can process audio, but there's no way to actually initiate a phone call. This change adds the entry point: load a call script, validate safety rules (legal hours, DNC list), set up the Twilio webhook server, place the call, and run the pipeline until completion. This is the final piece that makes the system end-to-end functional.

## What Changes

- Create call script loader (YAML → CallContext)
- Implement DNC (Do Not Call) list management
- Implement legal hours check (08:00-20:00 local time)
- Create webhook server (FastAPI) for Twilio call control and Media Streams
- Create main entry point that ties everything together: load script → check safety → place call → run pipeline → hangup
- Add Level 2 (telephony) integration tests with real phone calls

## Capabilities

### New Capabilities
- `call-script-loader`: Parse YAML call scripts into CallContext with validated configuration
- `call-safety`: DNC list check and legal hours enforcement before every outbound call
- `webhook-server`: FastAPI server handling Twilio webhooks (call status, Media Streams WebSocket)
- `outbound-call-runner`: Main entry point — orchestrates the full outbound call lifecycle

### Modified Capabilities

## Impact

- **Dependencies**: adds `fastapi`, `uvicorn` to pyproject.toml
- **Code**: new `src/call_runner.py`, `src/webhook.py`, `src/safety.py`, `src/script_loader.py`
- **Infrastructure**: requires publicly accessible URL for Twilio webhooks (ngrok for development)
- **Tests**: Level 2 tests that place real calls (requires all credentials + verified phone number)

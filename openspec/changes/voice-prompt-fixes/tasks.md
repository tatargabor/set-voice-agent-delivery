## 1. No-markdown system prompt

- [x] 1.1 Add TTS instruction to `_build_system_prompt()` in `agent.py` — no markdown, no emoji, plain spoken Hungarian
- [x] 1.2 Add TTS instruction to `_fast_ack()` prompt in `response_layers.py`
- [x] 1.3 Add TTS instruction to local agent prompt in `local_agent.py`

## 2. Outbound greeting

- [x] 2.1 Add `call_direction` field to `CallContext` (`inbound` | `outbound`, default `inbound`)
- [x] 2.2 Update greeting in `agent.py` to use direction-aware greeting
- [x] 2.3 Set `call_direction="outbound"` in webhook.py for `/api/call` and outbound phone calls

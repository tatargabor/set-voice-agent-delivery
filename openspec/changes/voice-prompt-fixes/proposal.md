## Why

Two voice UX issues: (1) Claude responses contain markdown formatting (`**`, `#`, etc.) that sounds wrong when read aloud by TTS, and (2) the outbound call greeting says "miben segíthetek?" as if the customer called us — but WE called THEM, so the greeting should explain why we're calling.

## What Changes

- System prompt: explicitly tell Claude this is a phone call, responses will be read aloud by TTS — no markdown, no special characters, no emojis, plain spoken Hungarian
- Outbound greeting: change from "Miben segíthetek?" to purpose-driven greeting like "Azért hívtam, mert elkészült a projekt és szeretnénk ha megnézné"
- Inbound greeting stays as-is (customer initiated, "miben segíthetek" is correct)

## Capabilities

### New Capabilities

### Modified Capabilities
- `deep-agent-toolbox`: System prompt update — no markdown in voice responses

## Impact

- **Code**: `src/agent.py` (system prompt), `src/response_layers.py` (fast ack prompt)
- No new dependencies

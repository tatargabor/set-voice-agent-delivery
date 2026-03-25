# Voice Agent — WebBuilder Kft.

AI voice agent: Soniox STT (magyar) + Claude (beszélgetés) + Google TTS (magyar) + Twilio (telefónia/WebRTC).

## Gyors indítás

```bash
pip install -e ".[dev]"
# .env kitöltése (lásd docs/SETUP.md)
ngrok http 8765
set -a && source .env && set +a && python -c "
from src.webhook import app, enable_inbound_mode
enable_inbound_mode()
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8765)
"
```

Widget: `https://<ngrok-url>/static/voice-widget.html`

Teljes telepítési útmutató: [docs/SETUP.md](docs/SETUP.md)

## Architektúra

```
Böngésző (WebRTC) / Telefon
    │
    ▼
Twilio (Media Streams WebSocket)
    │
    ▼
┌─────────────────────────────┐
│  FastAPI (port 8765)        │
│  ├── /twilio/voice (TwiML)  │
│  ├── /twilio/token (JWT)    │
│  ├── /twilio/media-stream   │
│  ├── /api/projects          │
│  └── /api/call (outbound)   │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  CallPipeline               │
│  ├── STT loop (Soniox)     │
│  ├── LLM loop (Claude)     │
│  │   ├── Fast ack (Haiku)  │
│  │   └── Deep (Sonnet)     │
│  │       ├── tool_use      │
│  │       └── local agent   │
│  └── TTS loop (Google)     │
└─────────────────────────────┘
```

## Költség

~$0.02-0.08 / hívás (browser), ~$0.10-0.15 / hívás (outbound telefon)

## Logok

`logs/calls/YYYY-MM-DD/YYYYMMDD_HHMMSS_customer.json` — transcript, költségek, tool calls, metrikák.

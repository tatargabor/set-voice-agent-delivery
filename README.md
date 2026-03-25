# Voice Agent — WebBuilder Kft.

AI voice agent: Soniox STT (magyar) + Claude (beszélgetés) + Google TTS (magyar) + Twilio (telefónia/WebRTC).

## Követelmények

- Python 3.11+
- ngrok (free tier OK)
- API kulcsok (lásd `.env` setup)

## Telepítés új gépen

```bash
git clone https://github.com/tatargabor/set-voice-agent-delivery.git
cd set-voice-agent-delivery
pip install -e ".[dev]"
```

## Indítás lépésről lépésre

### 1. API kulcsok (.env)

Hozd létre a `.env` fájlt a projekt gyökerében:

Szükséges kulcsok a `.env`-ben:

```
# Anthropic (Claude) — https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-...

# Soniox (STT) — https://soniox.com/
SONIOX_API_KEY=...

# Google Cloud (TTS) — https://console.cloud.google.com/
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Twilio (telefónia) — https://console.twilio.com/
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# Twilio browser client (WebRTC widget)
TWILIO_API_KEY_SID=SK...
TWILIO_API_KEY_SECRET=...
TWILIO_TWIML_APP_SID=AP...
```

### 2. ngrok tunnel indítása

```bash
ngrok http 8765
```

A kapott URL-t (pl. `https://xyz.ngrok-free.dev`) be kell állítani:
- Twilio Console → TwiML App → Voice Request URL: `https://xyz.ngrok-free.dev/twilio/voice`

### 3. Szerver indítása

```bash
# Env vars exportálása + szerver indítás
set -a && source .env && set +a && python -c "
from src.webhook import app, enable_inbound_mode
enable_inbound_mode()
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8765)
"
```

Háttérben:
```bash
set -a && source .env && set +a && python -c "
from src.webhook import app, enable_inbound_mode
enable_inbound_mode()
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8765)
" &
```

### 4. Voice widget megnyitása

Böngészőben: `https://<ngrok-url>/static/voice-widget.html`

1. Válassz projektet a dropdown-ból
2. (Opcionális) Add meg a neved
3. Kattints a mikrofon gombra

### 5. Leállítás

```bash
lsof -ti:8765 | xargs kill -9
```

## Konfiguráció

### config.yaml (alkalmazás beállítások)

```yaml
models:
  fast: claude-haiku-4-5        # Fast ack layer
  deep: claude-sonnet-4-6       # Deep response
  agent: claude-sonnet-4-6      # Local agent research

voice:
  max_sentences: 3              # Max mondatok per válasz
  max_tokens_tool_use: 150      # Tool_use válasz token limit
  max_tokens_agent: 100         # Local agent token limit
  max_tokens_stream: 300        # Streaming token limit
  endpoint_delay_ms: 1200       # Csend detektálás (ms)

research:
  mode: auto                    # tool_use | local_agent | auto
  agent_timeout_sec: 10
  agent_max_iterations: 3
  tool_timeout_sec: 15

projects_dir: /home/tg/code2
```

**Research mode-ok:**
- `tool_use` — Claude tool_use API (egyszerű kérdésekre)
- `local_agent` — helyi agent saját tool loop-pal (mélyebb kutatásra)
- `auto` — automatikus: kutatós kérdés → agent, egyéb → tool_use

## Architektúra

```
Böngésző (WebRTC)
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
│  └── /api/projects          │
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

## Költség (hívásonként)

~$0.02-0.13 attól függően milyen hosszú és mennyire kutatós:
- Claude: $0.005-0.12 (tokenektől függ)
- Google TTS: ~$0.01
- Twilio: ~$0.004 (browser) / $0.085 (outbound telefon)
- Soniox: ~$0.002/perc

## Logok

Hívás logok: `logs/calls/YYYY-MM-DD/YYYYMMDD_HHMMSS_customer.json`

Tartalmazza: transcript, költségek, tool calls, metrikák.

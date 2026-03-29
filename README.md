# set-voice-agent-delivery

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab.svg)](https://python.org)
[![Platform: Linux / macOS](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey.svg)]()

AI-powered voice agent for real-time phone conversations. Combines **Soniox STT** (speech-to-text), **Claude** (conversation engine), **Google Cloud TTS** (text-to-speech), and **Twilio** (telephony/WebRTC) into a low-latency voice pipeline.

Built as a [set-core](https://github.com/tatargabor/set-core) consumer project — developed and orchestrated using OpenSpec-driven parallel agents.

## How It Works

```
Browser (WebRTC) / Phone
    |
    v
Twilio (Media Streams WebSocket)
    |
    v
+-------------------------------+
|  FastAPI server (port 8765)   |
|  +-- /twilio/voice   (TwiML)  |
|  +-- /twilio/token   (JWT)    |
|  +-- /twilio/media-stream      |
|  +-- /api/projects             |
|  +-- /api/call (outbound)      |
+---------------+---------------+
                |
                v
+-------------------------------+
|  CallPipeline                 |
|  +-- STT loop  (Soniox)      |
|  +-- LLM loop  (Claude)      |
|  |   +-- Fast ack  (Haiku)   |
|  |   +-- Deep      (Sonnet)  |
|  |       +-- tool_use         |
|  |       +-- local agent      |
|  +-- TTS loop  (Google)      |
+-------------------------------+
```

**Pipeline stages:**

1. **Soniox STT** — real-time Hungarian speech recognition via WebSocket streaming. Configurable silence detection threshold for natural turn-taking.
2. **Claude conversation engine** — two-layer response system:
   - *Fast ack* (Haiku) — immediate acknowledgment while the deep layer thinks
   - *Deep response* (Sonnet) — full conversational reply with optional tool use or local agent research
3. **Google Cloud TTS** — Hungarian text-to-speech with Chirp3 HD voices. Audio streamed back as mulaw/8000 for Twilio compatibility.
4. **Twilio** — handles telephony (inbound/outbound calls) and browser-based WebRTC connections.

## Features

- **Real-time voice conversations** with sub-second latency
- **Browser widget** for in-browser calls (WebRTC via Twilio Client SDK)
- **Outbound calls** to any phone number via Twilio
- **Inbound call handling** with configurable project routing
- **Multi-project support** — each project gets its own system prompt, knowledge base, and call scripts
- **Research modes** — `tool_use` (API tool calls), `local_agent` (autonomous research loop), or `auto` (smart routing)
- **Call logging** — full transcripts, cost breakdown, tool calls, and latency metrics per call
- **Configurable models** — swap Claude models per layer (fast/deep/agent) in `config.yaml`

## Installation

**Prerequisites:** Python 3.11+, [ngrok](https://ngrok.com/), API keys for Anthropic, Soniox, Google Cloud TTS, and Twilio.

```bash
git clone https://github.com/tatargabor/set-voice-agent-delivery.git
cd set-voice-agent-delivery
pip install -e ".[dev]"
```

### API Keys

Create a `.env` file in the project root:

```env
# Anthropic (Claude) — https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-...

# Soniox (STT) — https://soniox.com/
SONIOX_API_KEY=...

# Google Cloud (TTS) — https://console.cloud.google.com/
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Twilio (telephony) — https://console.twilio.com/
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# Twilio browser client (WebRTC widget)
TWILIO_API_KEY_SID=SK...
TWILIO_API_KEY_SECRET=...
TWILIO_TWIML_APP_SID=AP...
```

| Service | Console | What you need |
|---------|---------|---------------|
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com/) | API key |
| **Soniox** | [soniox.com](https://soniox.com/) | Register, Dashboard, API Key |
| **Google Cloud** | [console.cloud.google.com](https://console.cloud.google.com/) | Project + Text-to-Speech API enabled + Service Account key (JSON) |
| **Twilio** | [console.twilio.com](https://console.twilio.com/) | Account SID + Auth Token + phone number. For WebRTC: API Key + TwiML App |

## Quick Start

```bash
# 1. Start ngrok tunnel
ngrok http 8765

# 2. Set the ngrok URL in Twilio Console:
#    Voice -> TwiML Apps -> Voice Request URL: https://<ngrok-url>/twilio/voice

# 3. Start the server
set -a && source .env && set +a && python -c "
from src.webhook import app, enable_inbound_mode
enable_inbound_mode()
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8765)
"
```

Open the voice widget in your browser: `https://<ngrok-url>/static/voice-widget.html`

1. Select a project from the dropdown
2. (Optional) Enter your name for caller identification
3. Click the microphone button to start a browser call
4. Click the phone button to place an outbound call to a number

## Configuration

Application settings live in `config.yaml` (API keys stay in `.env`):

```yaml
models:
  fast: claude-haiku-4-5        # Fast acknowledgment layer
  deep: claude-sonnet-4-6       # Deep response + tool use
  agent: claude-sonnet-4-6      # Local agent research

tts:
  voice_name: hu-HU-Chirp3-HD-Achernar
  language_code: hu-HU
  sample_rate: 8000

voice:
  max_sentences: 6              # Max sentences per response
  endpoint_delay_ms: 800        # Silence detection threshold (ms)

research:
  mode: auto                    # tool_use | local_agent | auto
  agent_timeout_sec: 10
  agent_max_iterations: 3
```

### Research Modes

| Mode | Best for | Description |
|------|----------|-------------|
| `tool_use` | Simple lookups | Claude API tool_use loop — each tool call is an API roundtrip |
| `local_agent` | Deep research | Local agent with its own tool loop, fewer API calls |
| `auto` | General use (default) | Routes research questions to agent, simple questions to tool_use |

## Cost

| Channel | Estimated cost per call |
|---------|------------------------|
| Browser (WebRTC) | ~$0.02 -- $0.08 |
| Outbound phone | ~$0.10 -- $0.15 |

Costs include STT, LLM tokens, TTS, and Twilio minutes.

## Call Logs

Every call is logged to `logs/calls/YYYY-MM-DD/`:

```
logs/calls/2026-03-28/20260328_143022_customer.json
```

Each log contains: full transcript, per-turn latency, token usage, cost breakdown, tool calls, and research results.

## Testing

```bash
# Unit tests (no API keys required)
python -m pytest tests/ -k "not twilio_provider and not google_tts and not soniox and not test_agent" -v

# Full test suite (requires all API keys)
python -m pytest tests/ -v
```

## Integration with set-core

This project is developed using [set-core](https://github.com/tatargabor/set-core) orchestration:

- **OpenSpec-driven development** — specifications in `openspec/specs/`, changes planned and executed by parallel agents
- **set-core commands** — `/opsx:apply`, `/opsx:verify`, `/set:sentinel` for autonomous development
- **Integration gates** — automated build, test, and merge validation

See [docs/SETUP.md](docs/SETUP.md) for the full setup guide (Hungarian).

## License

MIT

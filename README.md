# set-voice-agent-delivery

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab.svg)](https://python.org)
[![Platform: Linux / macOS](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey.svg)]()

**A real-time AI voice agent that answers phone calls and talks to your customers — built with Claude, streamed speech-to-text, and sub-second response latency.**

---

## The Story

We needed an AI agent that could pick up the phone and have a real conversation with customers — in Hungarian. Not a chatbot with a voice skin, but something that feels like talking to a knowledgeable colleague who knows your project inside out.

The problem with most voice AI is latency. You say something, wait three seconds, then hear a robotic answer. That's not a conversation — it's an interrogation. So we built a pipeline that starts speaking before the full response is ready, acknowledges you immediately with a fast model while a deeper model thinks, and handles interruptions naturally.

The result: **under one second from the moment you stop speaking to the moment the agent starts talking back.**

This project was built entirely using [set-core](https://github.com/ASetCoding/set-core) — an orchestration framework for Claude Code that manages parallel AI agents, structured specifications, and integration gates. Every feature started as an OpenSpec change, was decomposed into tasks, implemented by agents in parallel worktrees, and merged through automated quality gates. The development process itself is a showcase of what set-core enables: a complex real-time system, built incrementally, with each piece verified before merging.

---

## How It Works

```
Browser (WebRTC) or Phone
         |
         v
   Twilio Media Streams (WebSocket)
         |
         v
+-----------------------------------+
|  FastAPI Server (port 8765)       |
|                                   |
|  /twilio/voice     — TwiML        |
|  /twilio/token     — JWT (WebRTC) |
|  /twilio/media-stream — WebSocket |
|  /api/projects     — project list |
|  /api/call         — outbound     |
|  /static/          — voice widget |
+----------------+------------------+
                 |
                 v
+-----------------------------------+
|  CallPipeline (3 async loops)     |
|                                   |
|  STT Loop ──► Soniox (streaming)  |
|       |                           |
|  LLM Loop ──► Claude              |
|       |       ├─ Fast (Haiku)     |
|       |       └─ Deep (Sonnet)    |
|       |           ├─ tool_use     |
|       |           └─ local agent  |
|       |                           |
|  TTS Loop ──► Google Cloud TTS    |
+-----------------------------------+
```

### The Two-Layer Response System

This is the core innovation. When a customer speaks, two things happen simultaneously:

1. **Fast layer (Haiku, ~200ms)** — generates an immediate acknowledgment: *"I understand, let me look into that."* This gets synthesized and played back instantly so the customer knows they were heard.

2. **Deep layer (Sonnet)** — works on the real answer. It can call tools, search project files, or spin up a local research agent. When it's ready, it seamlessly takes over from the fast layer.

The customer never waits in silence. They hear a natural conversational flow while the heavy thinking happens in the background.

### Barge-In & Turn-Taking

If the customer starts speaking while the agent is talking, the agent stops immediately. The STT captures what the customer said, the pipeline cancels any queued audio, and a new response cycle begins. This mirrors how real conversations work — you can interrupt, and the other person adjusts.

---

## Features

- **Sub-second voice latency** — fast ack + streaming TTS means the agent responds almost immediately
- **Browser voice widget** — click a button and talk via WebRTC, no phone needed
- **Inbound & outbound calls** — receive calls on your Twilio number or dial out to any phone
- **Multi-project support** — each customer project gets its own knowledge base, system prompt, and call scripts
- **Research modes** — the agent can use API tool calls, spawn a local research agent, or auto-route between them
- **Call logging** — every call produces a JSON log with full transcript, per-turn latency, token usage, cost breakdown, and tool calls
- **Call summaries** — post-call Claude Haiku analysis extracts action items, questions, and customer sentiment
- **Prompt caching** — Anthropic prompt caching on deep responses reduces cost and latency on repeated context
- **Backchannel filtering** — ignores filler words ("mhm", "igen") during agent speech to prevent false barge-ins
- **Configurable everything** — swap models, voices, silence thresholds, research modes, and response lengths in `config.yaml`

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **ngrok** — tunnels your local server to the internet so Twilio can reach it ([download](https://ngrok.com/download))
- API keys for: **Anthropic** (Claude), **Soniox** (STT), **Google Cloud** (TTS), **Twilio** (telephony)

### 1. Clone & Install

```bash
git clone https://github.com/ASetCoding/set-voice-agent-delivery.git
cd set-voice-agent-delivery
pip install -e ".[dev]"
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```env
# Anthropic (Claude) — https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-...

# Soniox (STT) — https://soniox.com/
SONIOX_API_KEY=...

# Google Cloud (TTS) — https://console.cloud.google.com/
# Enable the Text-to-Speech API, create a service account, download the JSON key
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json

# Twilio (telephony) — https://console.twilio.com/
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# For the browser voice widget (WebRTC):
# Twilio Console → API Keys → Create API Key
# Twilio Console → TwiML Apps → Create TwiML App
TWILIO_API_KEY_SID=SK...
TWILIO_API_KEY_SECRET=...
TWILIO_TWIML_APP_SID=AP...
```

| Service | Console | What You Need |
|---------|---------|---------------|
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com/) | API key |
| **Soniox** | [soniox.com](https://soniox.com/) | Account + API key |
| **Google Cloud** | [console.cloud.google.com](https://console.cloud.google.com/) | Project with Text-to-Speech API enabled + service account JSON key |
| **Twilio** | [console.twilio.com](https://console.twilio.com/) | Account SID, Auth Token, phone number. For WebRTC: API Key + TwiML App |

### 3. Start the Services

You need three things running: the **Python server**, an **ngrok tunnel**, and your **environment loaded**.

**Terminal 1 — ngrok tunnel:**

```bash
ngrok http 8765
```

Copy the `https://...ngrok-free.dev` URL from the output.

**Terminal 2 — voice agent server:**

```bash
# Load environment variables and start the server
set -a && source .env && set +a
python -m src.inbound_server --port 8765
```

You should see:

```
=== Inbound Voice Agent Server ===
Listening on port 8765
```

### 4. Configure Twilio

**For the browser widget (WebRTC):**

1. Go to [Twilio Console → TwiML Apps](https://console.twilio.com/us1/develop/voice/manage/twiml-apps)
2. Open your TwiML App (or create one)
3. Set **Voice Request URL** to: `https://<your-ngrok-url>/twilio/voice`
4. Save

**For inbound phone calls:**

1. Go to [Twilio Console → Phone Numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
2. Click your phone number
3. Under **Voice**, set **"A Call Comes In"** webhook to: `https://<your-ngrok-url>/twilio/voice`
4. Save

### 5. Make a Call

**From browser:** Open `https://<your-ngrok-url>/static/voice-widget.html`
- Select a project from the dropdown
- Click the microphone button to start talking

**From phone:** Call your Twilio phone number — the agent will answer.

**Outbound call:**
```bash
set -a && source .env && set +a
python -m src --phone "+1234567890" --script call_scripts/website_followup.yaml
```

---

## Configuration

All application settings live in `config.yaml` — API keys stay in `.env`:

```yaml
language: hu                       # hu | en
company_name: Your Company Ltd.    # Used in greetings

models:
  fast: claude-haiku-4-5           # Fast acknowledgment layer (~200ms)
  deep: claude-sonnet-4-6          # Deep response + tool use (~1-3s)
  agent: claude-sonnet-4-6         # Local agent research

tts:
  voice_name: hu-HU-Chirp3-HD-Achernar  # Google TTS voice
  language_code: hu-HU
  sample_rate: 8000

voice:
  max_sentences: 6                 # Max sentences per response
  endpoint_delay_ms: 800           # Silence threshold for turn-taking (ms)

research:
  mode: auto                       # tool_use | local_agent | auto
  agent_timeout_sec: 10
  agent_max_iterations: 3
```

### Research Modes

| Mode | Best For | How It Works |
|------|----------|--------------|
| `tool_use` | Simple lookups | Claude's built-in tool calling — each tool is an API roundtrip |
| `local_agent` | Deep research | Spawns a local agent with its own tool loop, fewer API calls, more autonomy |
| `auto` | General use (default) | Routes research questions to the local agent, simple questions to tool_use |

### Adding Your Own Projects

Create a YAML file in your projects directory with project details, documentation links, and knowledge base. The agent will use this context when talking to customers about that specific project. See existing files in the repo for examples.

---

## Cost

| Channel | Estimated Cost Per Call (~1 min) |
|---------|----------------------------------|
| Browser (WebRTC) | ~$0.02 — $0.08 |
| Outbound phone | ~$0.10 — $0.15 |

Breakdown: Soniox STT + Claude tokens (Haiku + Sonnet) + Google TTS + Twilio minutes. Prompt caching reduces repeat-context costs significantly.

---

## Call Logs

Every call is automatically logged to `logs/calls/YYYY-MM-DD/`:

```
logs/calls/2026-03-28/20260328_143022_customer.json
```

Each log contains:
- Full transcript (customer + agent turns)
- Per-turn latency measurements
- Token usage per Claude call
- Cost breakdown by service
- Tool calls and research results
- Call summary with action items and sentiment

---

## Testing

```bash
# Unit tests (no API keys required)
python -m pytest tests/ -k "not twilio_provider and not google_tts and not soniox and not test_agent" -v

# Full test suite (requires all API keys configured)
python -m pytest tests/ -v
```

---

## Architecture Decisions

**Why Soniox for STT?** — Best-in-class Hungarian speech recognition with true streaming (word-by-word results over WebSocket). Most alternatives either don't support Hungarian well or only offer batch transcription.

**Why Google Cloud TTS?** — Chirp3 HD voices sound natural in Hungarian. The `mulaw/8000` output format is directly compatible with Twilio Media Streams, so no transcoding needed.

**Why two Claude models?** — A single model can't be both fast and thorough. Haiku gives you sub-200ms acknowledgments while Sonnet takes 1-3 seconds for a thoughtful, tool-augmented response. The customer hears a natural conversation flow instead of dead air.

**Why FastAPI + WebSocket?** — Twilio Media Streams sends audio as a continuous WebSocket stream. FastAPI's async support lets us run STT, LLM, and TTS loops concurrently without threading complexity.

---

## Built With set-core

This project was developed using [set-core](https://github.com/ASetCoding/set-core), an orchestration framework for Claude Code. Here's how that shaped the development:

Every feature — from the initial STT provider to the two-layer response system — started as an **OpenSpec change**. Each change followed the same lifecycle:

1. **Explore** — think through the problem, clarify requirements
2. **Propose** — write a structured proposal with scope and constraints
3. **Specify** — create detailed specs and design documents
4. **Decompose** — break the work into implementable tasks
5. **Apply** — agents implement tasks in isolated worktrees
6. **Verify** — automated gates check build, tests, and design compliance
7. **Archive** — merge to main and close the change

Multiple changes ran in parallel. While one agent implemented the call pipeline, another worked on the safety module, and a third built the webhook server. set-core's sentinel supervisor monitored all agents, caught integration issues, and restarted failed builds automatically.

The `openspec/changes/` directory contains the full history of every structured change that built this project — from `env-and-providers` (the first API integrations) through `prompt-caching` (the latest optimization).

---

## License

MIT

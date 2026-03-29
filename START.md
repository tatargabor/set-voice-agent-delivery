# Starting the Voice Agent Service

This file describes how to start all components needed for the voice agent. When the user says "start the service" or "indítsd a szolgáltatást", follow these steps in order.

## Prerequisites

- `.env` file exists in project root with all API keys
- `ngrok` is installed
- Python dependencies installed (`pip install -e ".[dev]"`)

## Step 1: Start the server

```bash
set -a && source .env && set +a && python -m src.inbound_server --port 8765
```

Run this in the background. Expected output:
```
config_loaded
inbound_mode_enabled
=== Inbound Voice Agent Server ===
Listening on port 8765
```

## Step 2: Start ngrok tunnel

```bash
ngrok http 8765
```

Run this in the background. Then get the public URL:

```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'])"
```

The current stable ngrok URL is: `https://dax-rostral-unfrankly.ngrok-free.dev`
(This URL persists across restarts if using a paid ngrok plan. On free tier it changes every restart.)

## Step 3: Verify

Check both processes are running:
```bash
pgrep -f "src.inbound_server" && echo "server: OK" || echo "server: NOT RUNNING"
pgrep -a ngrok | grep -q "http 8765" && echo "ngrok: OK" || echo "ngrok: NOT RUNNING"
```

## Step 4: Open the voice widget

The browser voice client is at:
```
https://<ngrok-url>/static/voice-widget.html
```

Give this URL to the user so they can test.

## Restarting the server

If the server needs to restart (e.g., config change):

```bash
pgrep -f "src.inbound_server" | xargs kill 2>/dev/null
sleep 1
set -a && source .env && set +a && python -m src.inbound_server --port 8765
```

## Stopping everything

```bash
pgrep -f "src.inbound_server" | xargs kill 2>/dev/null
pgrep -f "ngrok http" | xargs kill 2>/dev/null
```

## Twilio webhook config

The ngrok URL must be configured in Twilio Console:
- **TwiML App** (for browser widget): Voice Request URL = `https://<ngrok-url>/twilio/voice`
- **Phone number** (for inbound phone calls): "A Call Comes In" webhook = `https://<ngrok-url>/twilio/voice`

## Language switching

Edit `config.yaml`:

```yaml
# Hungarian
language: hu
tts:
  voice_name: hu-HU-Chirp3-HD-Achernar
  language_code: hu-HU

# English
language: en
tts:
  voice_name: en-US-Chirp3-HD-Achernar
  language_code: en-US
```

Restart the server after changing language.

# Telepítés és beüzemelés

## 1. Klónozás és függőségek

```bash
git clone https://github.com/tatargabor/set-voice-agent-delivery.git
cd set-voice-agent-delivery
pip install -e ".[dev]"
```

Követelmények: Python 3.11+, ngrok

## 2. API kulcsok (.env)

Hozd létre a `.env` fájlt a projekt gyökerében:

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

### API kulcsok beszerzése

| Szolgáltatás | Hol | Mit kell |
|-------------|-----|----------|
| **Anthropic** | https://console.anthropic.com/ | API key létrehozás |
| **Soniox** | https://soniox.com/ | Regisztráció → Dashboard → API Key |
| **Google Cloud** | https://console.cloud.google.com/ | 1) Projekt létrehozás, 2) Text-to-Speech API engedélyezés, 3) Service Account kulcs (JSON) letöltés |
| **Twilio** | https://console.twilio.com/ | Account SID + Auth Token a Dashboard-on. Telefonszám: Buy a Number |

### Twilio browser client beállítás

A WebRTC widget-hez 3 extra Twilio beállítás kell:

1. **API Key**: Console → Account → API keys → Create API Key → SID (`SK...`) és Secret
2. **TwiML App**: Console → Voice → TwiML Apps → Create → Voice Request URL: `https://<ngrok-url>/twilio/voice` → SID (`AP...`)
3. Mindhárom értéket a `.env`-be

## 3. ngrok tunnel

```bash
ngrok http 8765
```

A kapott URL-t (pl. `https://xyz.ngrok-free.dev`) be kell állítani:
- Twilio Console → TwiML App → Voice Request URL: `https://xyz.ngrok-free.dev/twilio/voice`

Megjegyzés: ngrok free tier-en az URL minden újraindítás után változik — frissítsd a TwiML App-ban is.

## 4. Szerver indítása

```bash
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

## 5. Használat

### Browser voice widget

Böngészőben: `https://<ngrok-url>/static/voice-widget.html`

1. Válassz projektet a dropdown-ból
2. (Opcionális) Add meg a neved
3. Mikrofon gomb: böngészőből beszélsz az agent-tel
4. Telefon gomb: outbound hívást indít a beírt számra

### Leállítás

```bash
lsof -ti:8765 | xargs kill -9
```

## 6. Konfiguráció (config.yaml)

Az alkalmazás beállítások a `config.yaml`-ban vannak (API kulcsok maradnak `.env`-ben):

```yaml
models:
  fast: claude-haiku-4-5          # Fast ack layer
  deep: claude-sonnet-4-6         # Deep response
  agent: claude-sonnet-4-6        # Local agent research

tts:
  voice_name: hu-HU-Chirp3-HD-Achernar  # Google TTS hang
  language_code: hu-HU
  sample_rate: 8000

voice:
  max_sentences: 3                # Max mondatok per válasz
  max_tokens_tool_use: 150        # Tool_use token limit
  max_tokens_agent: 100           # Local agent token limit
  max_tokens_stream: 300          # Streaming token limit
  endpoint_delay_ms: 1200         # Csend detektálás (ms)

research:
  mode: auto                      # tool_use | local_agent | auto
  agent_timeout_sec: 10
  agent_max_iterations: 3
  tool_timeout_sec: 15

projects_dir: /home/tg/code2      # Projekt könyvtár
```

### Research mode-ok

| Mode | Mikor használja | Leírás |
|------|----------------|--------|
| `tool_use` | Egyszerű kérdések | Claude API tool_use loop — minden tool call API roundtrip |
| `local_agent` | Mélyebb kutatás | Helyi agent saját tool loop-pal, kevesebb API hívás |
| `auto` | Alapértelmezett | Kutatós kérdés → agent, egyéb → tool_use |

### Elérhető TTS hangok

```bash
# Magyar hangok listázása
python -c "
from google.cloud import texttospeech
client = texttospeech.TextToSpeechClient()
for v in client.list_voices(language_code='hu-HU').voices:
    gender = texttospeech.SsmlVoiceGender(v.ssml_gender).name
    print(f'{v.name} ({gender})')
"
```

## 7. Tesztek

```bash
# Összes unit test (nincs API kulcs szükséges)
python -m pytest tests/ -k "not twilio_provider and not google_tts and not soniox and not test_agent" -v

# Teljes teszt suite (API kulcsok kellenek)
python -m pytest tests/ -v
```

## Hibaelhárítás

| Probléma | Megoldás |
|----------|---------|
| "Twilio browser client not configured" | `.env`-ben hiányzik `TWILIO_API_KEY_SID`, `TWILIO_API_KEY_SECRET`, vagy `TWILIO_TWIML_APP_SID` |
| Angol férfi hang szól | A szerver foglalt volt (`_inbound_busy`), újraindítás segít |
| Nem hallatszik hang böngészőben | Ismert: TTS→böngésző audio irány probléma, telefonos hívás működik |
| "Address already in use" | `lsof -ti:8765 \| xargs kill -9` és újraindítás |
| Projekt lista üres | `set-project list` nincs telepítve, vagy nincs regisztrált projekt |

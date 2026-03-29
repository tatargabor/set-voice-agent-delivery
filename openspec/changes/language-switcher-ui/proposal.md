## Why

Currently, switching the voice agent's language requires editing `config.yaml` and restarting the server. For demos and testing, users need to toggle between English and Hungarian quickly — directly from the browser widget, without touching the server.

## What Changes

- Add a language toggle (EN/HU) to the voice widget UI
- Add a `POST /api/config` endpoint that updates `config.yaml` language + TTS settings at runtime
- Hot-reload the in-memory config so the next call uses the new language without server restart
- Widget reflects the active language immediately (UI text + toggle state)

## Capabilities

### New Capabilities
- `language-switcher`: Runtime language switching via widget UI — toggle between configured languages, persist to config.yaml, hot-reload settings, update widget i18n

### Modified Capabilities

## Impact

- `static/voice-widget.html` — new toggle element
- `static/voice-widget.js` — toggle handler, calls POST /api/config, refreshes UI text
- `src/webhook.py` — new `POST /api/config` endpoint
- `src/config.py` — hot-reload mechanism (update singleton settings)
- `config.yaml` — written to on language switch

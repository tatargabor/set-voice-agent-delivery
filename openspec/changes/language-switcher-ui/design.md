## Context

The voice agent supports Hungarian and English via the i18n module. Language is set in `config.yaml` and loaded once at startup into a singleton `AppSettings`. Changing language currently requires editing the file and restarting the server.

The widget already fetches `GET /api/config` to get the active language and company name, then renders all UI text accordingly.

Key files:
- `src/config.py` — `AppSettings` singleton, `get_settings()`, `load_app_settings()`
- `src/i18n.py` — all text dictionaries keyed by language, `get_text()` uses `get_settings().language`
- `static/voice-widget.js` — `loadConfig()` fetches language, sets `t = UI_TEXTS[lang]`
- `config.yaml` — `language`, `tts.voice_name`, `tts.language_code`

## Goals / Non-Goals

**Goals:**
- Toggle language (EN/HU) from the voice widget without server restart
- Persist the choice to `config.yaml` so it survives restarts
- Update widget UI text immediately after toggle
- Next call uses the new language (STT hints, Claude prompts, TTS voice)

**Non-Goals:**
- Adding new languages beyond hu/en (existing i18n already supports this pattern)
- Per-call language selection (toggle is global)
- Changing language mid-call

## Decisions

**1. POST /api/config endpoint for language update**
The widget sends `POST /api/config` with `{"language": "en"}` or `{"language": "hu"}`. The endpoint:
- Validates language is "hu" or "en"
- Updates the in-memory `AppSettings` singleton fields: `language`, `tts.voice_name`, `tts.language_code`
- Writes updated values to `config.yaml` via PyYAML
- Returns the new config state

Alternative: WebSocket push — overkill for a toggle that changes once per session.

**2. Hot-reload via settings mutation**
Rather than rebuilding the singleton, directly mutate the existing `AppSettings` object fields. All code already calls `get_settings()` which returns the singleton, so changes propagate immediately to the next call's `get_text()` lookups.

Alternative: Add a `reload_settings()` that re-reads config.yaml — more complex, risk of partial state.

**3. Language-to-TTS voice mapping**
Store a simple mapping dict in config.py:
```python
LANGUAGE_TTS_MAP = {
    "hu": {"voice_name": "hu-HU-Chirp3-HD-Achernar", "language_code": "hu-HU"},
    "en": {"voice_name": "en-US-Chirp3-HD-Achernar", "language_code": "en-US"},
}
```
When language changes, TTS settings are updated from this map.

**4. Widget toggle as a pill/button pair**
Simple EN|HU toggle in the widget header. Clicking switches language, calls POST, refreshes UI text. No page reload needed.

## Risks / Trade-offs

- [Config file write race] If two users toggle simultaneously, last write wins → acceptable for single-user demo tool
- [Mid-call language change] If toggled during an active call, the running pipeline keeps its original language since the agent/pipeline are already initialized → acceptable, next call picks up new language

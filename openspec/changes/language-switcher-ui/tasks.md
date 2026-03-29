## 1. Backend — POST /api/config + hot-reload

- [x] 1.1 Add `LANGUAGE_TTS_MAP` dict to `src/config.py` mapping language codes to TTS voice/language settings
- [x] 1.2 Add `update_language(lang)` function to `src/config.py` that mutates the AppSettings singleton and updates `config.yaml` on disk
- [x] 1.3 Add `POST /api/config` endpoint to `src/webhook.py` — accepts `{"language": "hu"|"en"}`, calls `update_language()`, returns updated config
- [x] 1.4 Validate language input — return HTTP 400 for invalid values

## 2. Widget — language toggle UI

- [x] 2.1 Add EN/HU toggle pill to `static/voice-widget.html` header area (between title and project selector)
- [x] 2.2 Add toggle click handler in `static/voice-widget.js` — POST to `/api/config`, update `t` variable, refresh all UI text
- [x] 2.3 Initialize toggle state from `GET /api/config` response in `loadConfig()`
- [x] 2.4 Style the toggle — active language highlighted, inactive greyed out

## 3. Verification

- [x] 3.1 Manual test: toggle EN→HU→EN in widget, verify all UI text switches
- [ ] 3.2 Manual test: toggle language, make a call, verify agent speaks in the new language

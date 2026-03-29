## ADDED Requirements

### Requirement: Language toggle in widget
The voice widget displays a language toggle (EN / HU) that allows switching the agent's language without server restart.

#### Scenario: User switches from English to Hungarian
- **WHEN** the user clicks the HU button in the language toggle
- **THEN** a POST request is sent to `/api/config` with `{"language": "hu"}`
- **THEN** the widget UI text updates to Hungarian immediately
- **THEN** the toggle visually reflects HU as active

#### Scenario: User switches from Hungarian to English
- **WHEN** the user clicks the EN button in the language toggle
- **THEN** a POST request is sent to `/api/config` with `{"language": "en"}`
- **THEN** the widget UI text updates to English immediately
- **THEN** the toggle visually reflects EN as active

### Requirement: POST /api/config endpoint
The server accepts language changes via POST and updates runtime config.

#### Scenario: Valid language change
- **WHEN** `POST /api/config` receives `{"language": "en"}` or `{"language": "hu"}`
- **THEN** the in-memory AppSettings is updated (language, tts.voice_name, tts.language_code)
- **THEN** `config.yaml` is written with the new values
- **THEN** the response returns `{"language": "...", "company_name": "..."}`

#### Scenario: Invalid language
- **WHEN** `POST /api/config` receives a language not in `["hu", "en"]`
- **THEN** the endpoint returns HTTP 400 with an error message
- **THEN** no settings are changed

### Requirement: Hot-reload settings
The settings singleton is mutated in-place so all subsequent calls to `get_text()` and `get_settings()` return the new language without restart.

#### Scenario: Next call uses new language
- **WHEN** language is switched via POST /api/config
- **THEN** the next inbound call uses the new language for STT hints, Claude prompts, TTS voice, and all i18n text

### Requirement: Widget loads active language on startup
The toggle initializes to the correct state based on the server's current language.

#### Scenario: Widget opened after language was previously set
- **WHEN** the widget page loads
- **THEN** `GET /api/config` returns the current language
- **THEN** the toggle shows the active language correctly

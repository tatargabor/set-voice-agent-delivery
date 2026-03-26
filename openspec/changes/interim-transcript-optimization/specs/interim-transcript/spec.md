## ADDED Requirements

### Requirement: TranscriptEvent type
The STT provider interface SHALL yield `TranscriptEvent` objects instead of raw strings. Each event SHALL contain a `text` field (the transcript string) and an `is_interim` boolean field (True for speculative, False for finalized transcripts).

#### Scenario: Final transcript event
- **WHEN** Soniox detects endpoint (`<fin>` or `<end>` token)
- **THEN** the provider yields a `TranscriptEvent(text="...", is_interim=False)`

#### Scenario: Interim transcript event
- **WHEN** interim is enabled AND at least `interim_min_words` words have accumulated AND at least `interim_silence_ms` milliseconds have passed since the last token
- **THEN** the provider yields a `TranscriptEvent(text="...", is_interim=True)` followed later by a final event

#### Scenario: Interim disabled
- **WHEN** `interim_enabled` is False in config
- **THEN** the provider SHALL only yield final events (same behavior as before)

### Requirement: Interim silence detection
The Soniox STT provider SHALL detect silence gaps during active speech by using a timeout mechanism on the event receive loop. The silence threshold SHALL be configurable via `interim_silence_ms` (default: 500ms).

#### Scenario: Silence detected with enough words
- **WHEN** no new token arrives for `interim_silence_ms` AND accumulated word count >= `interim_min_words`
- **THEN** an interim TranscriptEvent is yielded with the accumulated text

#### Scenario: Silence detected with insufficient words
- **WHEN** no new token arrives for `interim_silence_ms` AND accumulated word count < `interim_min_words`
- **THEN** no interim event is yielded; the provider continues waiting

#### Scenario: Token arrives before silence threshold
- **WHEN** a new token arrives before `interim_silence_ms` elapses
- **THEN** the token is accumulated and the silence timer resets

### Requirement: Speculative LLM execution
The pipeline SHALL start LLM processing on interim transcripts speculatively. If the final transcript matches the interim, the speculative result is used. If they differ, the speculative task is cancelled and restarted with the final text.

#### Scenario: Interim matches final
- **WHEN** an interim transcript is received AND the LLM starts processing AND the subsequent final transcript text equals the interim text
- **THEN** the LLM result from the interim is used without restart

#### Scenario: Interim differs from final
- **WHEN** an interim transcript is received AND the LLM starts processing AND the subsequent final transcript text differs from the interim text
- **THEN** the speculative LLM task is cancelled, the TTS queue is cleared, and a new LLM task is started with the final transcript

#### Scenario: Final arrives without preceding interim
- **WHEN** a final transcript arrives without a preceding interim for that utterance
- **THEN** the pipeline processes it normally (no speculative behavior)

### Requirement: Interim configuration
The voice config SHALL support interim transcript settings: `interim_enabled` (bool, default true), `interim_min_words` (int, default 3), and `interim_silence_ms` (int, default 500).

#### Scenario: Default configuration
- **WHEN** no interim config is specified in config.yaml
- **THEN** interim is enabled with min_words=3 and silence_ms=500

#### Scenario: Custom configuration
- **WHEN** config.yaml contains `interim_enabled: false`
- **THEN** interim transcript detection is disabled and only final transcripts are yielded

### Requirement: Reduced endpoint delay
The default `endpoint_delay_ms` SHALL be reduced from 1200ms to 800ms to complement the interim transcript feature.

#### Scenario: New default endpoint delay
- **WHEN** endpoint_delay_ms is not explicitly set in config.yaml
- **THEN** the default value is 800ms

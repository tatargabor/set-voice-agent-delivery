## ADDED Requirements

### Requirement: Collect Claude API usage per request
The system SHALL capture `input_tokens` and `output_tokens` from every Claude API response and accumulate them in `CallMetrics`.

#### Scenario: Agent responds to customer
- **WHEN** `ConversationAgent.respond()` or `get_greeting()` completes
- **THEN** the returned usage data SHALL be added to `CallMetrics.claude_input_tokens` and `CallMetrics.claude_output_tokens`, and `claude_requests` SHALL be incremented

### Requirement: Track TTS character count
The system SHALL count the total characters sent to Google TTS during a call.

#### Scenario: TTS synthesizes agent response
- **WHEN** text is sent to `GoogleTTSProvider.synthesize_stream()`
- **THEN** `CallMetrics.tts_chars` SHALL be incremented by `len(text)`

### Requirement: Track STT audio duration
The system SHALL capture the total processed audio milliseconds from Soniox events.

#### Scenario: STT processes audio
- **WHEN** a Soniox event with `total_audio_proc_ms > 0` is received
- **THEN** `CallMetrics.stt_audio_ms` SHALL be updated to the latest `total_audio_proc_ms` value

### Requirement: Fetch Twilio call price post-call
The system SHALL fetch the actual call price from Twilio after the call ends.

#### Scenario: Call completed
- **WHEN** the call ends and hangup is confirmed
- **THEN** the system SHALL call `calls(sid).fetch()` and store `price` and `duration` in CallMetrics

### Requirement: Measure per-turn response latency
The system SHALL measure the time from receiving a customer transcript to producing an agent response for each turn.

#### Scenario: Agent processes customer speech
- **WHEN** a transcript enters the LLM loop and a response is produced
- **THEN** the elapsed time in milliseconds SHALL be appended to `CallMetrics.response_times_ms`

### Requirement: Count barge-in events
The system SHALL count how many times the customer interrupted the agent during TTS playback.

#### Scenario: Barge-in detected
- **WHEN** STT detects speech during SPEAKING state
- **THEN** `CallMetrics.barge_in_count` SHALL be incremented

### Requirement: Calculate per-provider costs
The system SHALL calculate costs for each provider from collected metrics using known pricing rates.

#### Scenario: Cost calculation after call
- **WHEN** all metrics are collected
- **THEN** the system SHALL compute: Twilio cost (from API price), Claude cost (tokens × rate), Google TTS cost (chars × $4/1M), Soniox STT cost (audio_ms → minutes × $0.002/min)

### Requirement: Mask phone numbers
The system SHALL mask phone numbers before writing to logs. Format: keep country code + first 2 digits + last 4, mask middle with `***`.

#### Scenario: Phone number masking
- **WHEN** `+36203911669` is masked
- **THEN** the result SHALL be `+3620***1669`

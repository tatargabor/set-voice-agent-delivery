## ADDED Requirements

### Requirement: Streaming speech-to-text via Soniox WebSocket
The system SHALL implement `SonioxSTTProvider` conforming to the `STTProvider` ABC. It SHALL use the Soniox async WebSocket API (`AsyncRealtimeSTTSession`) with model `stt-rt-v4` for real-time transcription.

#### Scenario: Successful streaming transcription
- **WHEN** audio chunks are sent via `transcribe_stream()`
- **THEN** the provider SHALL yield partial transcript strings as tokens arrive from Soniox

#### Scenario: Final transcript after speech endpoint
- **WHEN** Soniox endpoint detection fires (speaker stops talking)
- **THEN** the provider SHALL yield the finalized transcript text

### Requirement: Hungarian language configuration
The system SHALL configure Soniox with `language_hints=["hu"]` and `language_hints_strict=True` to lock recognition to Hungarian.

#### Scenario: Hungarian speech recognized
- **WHEN** Hungarian audio is streamed
- **THEN** transcription output SHALL be Hungarian text

### Requirement: Twilio-compatible audio format
The system SHALL accept mulaw 8kHz mono audio (the format Twilio Media Streams provides) by configuring `audio_format="mulaw"`, `sample_rate=8000`, `num_channels=1`.

#### Scenario: mulaw audio input
- **WHEN** mulaw 8kHz audio bytes are sent to `transcribe_stream()`
- **THEN** Soniox SHALL decode and transcribe them without additional format conversion

### Requirement: Connection lifecycle
The system SHALL manage the WebSocket connection lifecycle via `connect()` and `disconnect()` methods.

#### Scenario: Connect and disconnect
- **WHEN** `connect()` is called
- **THEN** a WebSocket session is established with Soniox
- **WHEN** `disconnect()` is called
- **THEN** the session is closed cleanly

#### Scenario: Connection drop during transcription
- **WHEN** the WebSocket connection drops unexpectedly
- **THEN** the provider SHALL raise an exception (reconnection is handled by the caller)

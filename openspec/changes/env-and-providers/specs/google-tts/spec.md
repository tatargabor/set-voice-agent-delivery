## ADDED Requirements

### Requirement: Streaming text-to-speech via Google Cloud TTS
The system SHALL implement `GoogleTTSProvider` conforming to the `TTSProvider` ABC. It SHALL use the Google Cloud Text-to-Speech API to convert text into audio.

#### Scenario: Successful speech synthesis
- **WHEN** `synthesize_stream(text)` is called with Hungarian text
- **THEN** the provider SHALL yield audio bytes chunks

### Requirement: Hungarian voice configuration
The system SHALL use a Hungarian (`hu-HU`) neural voice from Google Cloud TTS.

#### Scenario: Hungarian text synthesized
- **WHEN** Hungarian text is provided
- **THEN** the output audio SHALL be spoken in Hungarian with a natural-sounding neural voice

### Requirement: Twilio-compatible audio output
The system SHALL output mulaw 8kHz mono audio to match Twilio Media Streams format, avoiding transcoding.

#### Scenario: Audio format matches Twilio
- **WHEN** TTS generates audio
- **THEN** output SHALL be mulaw 8000Hz mono, directly playable through Twilio Media Streams

### Requirement: Connection lifecycle
The system SHALL manage the Google Cloud TTS client lifecycle via `connect()` and `disconnect()` methods.

#### Scenario: Connect and disconnect
- **WHEN** `connect()` is called
- **THEN** a Google Cloud TTS client is initialized
- **WHEN** `disconnect()` is called
- **THEN** the client resources are released

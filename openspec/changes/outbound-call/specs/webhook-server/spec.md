## ADDED Requirements

### Requirement: Twilio voice webhook
The system SHALL provide a `POST /twilio/voice` endpoint that returns TwiML instructing Twilio to start a Media Stream WebSocket connection.

#### Scenario: Twilio calls the webhook
- **WHEN** Twilio sends a POST request to `/twilio/voice` after the call connects
- **THEN** the server SHALL respond with TwiML containing a `<Connect><Stream>` element pointing to the Media Stream WebSocket URL

### Requirement: Media Streams WebSocket endpoint
The system SHALL provide a WebSocket endpoint at `/twilio/media-stream` that handles bidirectional audio with Twilio.

#### Scenario: Twilio connects WebSocket
- **WHEN** Twilio establishes a WebSocket connection to `/twilio/media-stream`
- **THEN** the server SHALL accept the connection and begin forwarding audio to/from the CallPipeline

#### Scenario: Audio flows through WebSocket
- **WHEN** Twilio sends `media` messages containing base64 audio
- **THEN** the server SHALL decode the audio and feed it to the pipeline's STT input
- **WHEN** the pipeline produces TTS audio
- **THEN** the server SHALL encode it as base64 and send it back as Twilio `media` messages

### Requirement: Server lifecycle
The FastAPI server SHALL start before the call is placed and shut down after the call ends.

#### Scenario: Server startup
- **WHEN** an outbound call is about to be placed
- **THEN** the webhook server SHALL be running and accessible at the configured URL before `place_call()` is invoked

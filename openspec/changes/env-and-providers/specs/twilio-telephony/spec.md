## ADDED Requirements

### Requirement: Outbound call placement via Twilio REST API
The system SHALL implement `TwilioTelephonyProvider` conforming to the `TelephonyProvider` ABC. It SHALL place outbound calls using the Twilio REST API.

#### Scenario: Successful outbound call
- **WHEN** `place_call(phone_number, webhook_url)` is called
- **THEN** Twilio SHALL initiate a call from `TWILIO_PHONE_NUMBER` to the target number, using the webhook URL for call control
- **THEN** the method SHALL return the Twilio Call SID

#### Scenario: Invalid phone number
- **WHEN** `place_call()` is called with an invalid number
- **THEN** the provider SHALL raise an exception with the Twilio error details

### Requirement: Hang up active call
The system SHALL terminate active calls via the Twilio REST API.

#### Scenario: Successful hangup
- **WHEN** `hangup(call_sid)` is called for an active call
- **THEN** the call SHALL be terminated

### Requirement: Bidirectional audio via Media Streams WebSocket
The system SHALL receive inbound audio and send outbound audio through Twilio Media Streams WebSocket protocol.

#### Scenario: Receive audio stream
- **WHEN** `get_audio_stream(call_sid)` is called
- **THEN** the provider SHALL yield raw mulaw 8kHz audio bytes decoded from Twilio's base64 JSON messages

#### Scenario: Send audio to call
- **WHEN** `send_audio(call_sid, audio_bytes)` is called
- **THEN** the provider SHALL encode the audio as base64 and send it as a Twilio media message

### Requirement: Twilio credential management
The system SHALL use `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER` from environment variables. Credentials SHALL NOT be hardcoded.

#### Scenario: Credentials loaded from environment
- **WHEN** the provider is initialized
- **THEN** it SHALL read Twilio credentials from environment variables

#### Scenario: Missing credentials
- **WHEN** required Twilio environment variables are not set
- **THEN** initialization SHALL fail with a clear error message

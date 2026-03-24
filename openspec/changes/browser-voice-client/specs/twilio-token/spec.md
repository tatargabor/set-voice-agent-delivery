## ADDED Requirements

### Requirement: Generate Access Token for browser clients
The system SHALL provide a `GET /twilio/token` endpoint that returns a short-lived JWT for Twilio Client SDK authentication.

#### Scenario: Token request
- **WHEN** a browser requests `GET /twilio/token`
- **THEN** the system SHALL return a JSON response with a valid Access Token containing a VoiceGrant

#### Scenario: Token with identity
- **WHEN** a browser requests `GET /twilio/token?identity=gabor`
- **THEN** the token identity SHALL be set to "gabor" for caller identification

#### Scenario: Token expiry
- **WHEN** a token is generated
- **THEN** it SHALL expire after 3600 seconds (1 hour)

### Requirement: Twilio setup automation
The system SHALL provide a setup script or command that creates the required Twilio resources (TwiML App + API Key).

#### Scenario: First-time setup
- **WHEN** `python -m src.twilio_setup` is run
- **THEN** it SHALL create a TwiML App and API Key, and output the env vars to add to `.env`

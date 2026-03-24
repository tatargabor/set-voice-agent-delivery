## ADDED Requirements

### Requirement: Accept incoming calls
The system SHALL accept incoming calls on the configured Twilio phone number and run the voice agent pipeline.

#### Scenario: Known caller
- **WHEN** a known phone number calls the Twilio number
- **THEN** the system SHALL greet the caller by name and run the pipeline with their customer context

#### Scenario: Unknown caller
- **WHEN** an unknown phone number calls
- **THEN** the system SHALL use default context and ask for the caller's name

### Requirement: Persistent server mode
The system SHALL provide a persistent server mode (`python -m src.inbound_server`) that runs continuously and handles incoming calls.

#### Scenario: Server startup
- **WHEN** `python -m src.inbound_server` is started
- **THEN** the webhook server SHALL start and listen for incoming Twilio calls indefinitely

#### Scenario: Multiple calls in sequence
- **WHEN** one call ends and another comes in
- **THEN** the server SHALL handle the new call without restart

### Requirement: One call at a time
The system SHALL handle one call at a time for MVP. Concurrent calls SHALL be rejected with a polite message.

#### Scenario: Call while busy
- **WHEN** a call comes in while another is active
- **THEN** the system SHALL respond with TwiML saying "Jelenleg foglalt vagyok, kérem hívjon később" and hang up

### Requirement: GDPR recording notice on inbound
The system SHALL include a recording notice in the greeting for inbound calls, same as outbound.

#### Scenario: Inbound greeting
- **WHEN** an inbound call connects
- **THEN** the agent SHALL inform the caller that the call may be recorded

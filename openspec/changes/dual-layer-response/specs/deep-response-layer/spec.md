## ADDED Requirements

### Requirement: Deep response via Opus in parallel
The system SHALL start generating a deep response via Claude Opus in parallel with the fast acknowledgment.

#### Scenario: Parallel execution
- **WHEN** customer speech is received
- **THEN** the fast ack (Haiku) and deep response (Opus) SHALL start simultaneously

### Requirement: Deep response follows fast ack
The deep response SHALL be queued for TTS after the fast ack finishes playing.

#### Scenario: Response ordering
- **WHEN** both fast ack and deep response are ready
- **THEN** the customer SHALL hear the fast ack first, then the deep response

### Requirement: Conversation history includes both layers
Both the fast ack and deep response SHALL be recorded in conversation history as assistant messages.

#### Scenario: History tracking
- **WHEN** a dual-layer response completes
- **THEN** the conversation history SHALL contain both the ack and the substantive response

## ADDED Requirements

### Requirement: Wait for playback completion via mark event
The system SHALL send a Twilio `mark` message after the last TTS audio chunk and wait for Twilio's mark callback before transitioning from SPEAKING to LISTENING.

#### Scenario: Normal TTS playback
- **WHEN** all TTS audio chunks have been sent to Twilio
- **THEN** the system SHALL send a `mark` event with a unique name and wait for Twilio's mark confirmation before transitioning to LISTENING

#### Scenario: Mark timeout
- **WHEN** the mark confirmation does not arrive within 5 seconds
- **THEN** the system SHALL log a warning and transition to LISTENING anyway

### Requirement: Clear audio buffer on barge-in
The system SHALL send a Twilio `clear` message when barge-in is detected to immediately stop audio playback on the caller's end.

#### Scenario: Customer interrupts agent speech
- **WHEN** STT detects customer speech during SPEAKING state
- **THEN** the system SHALL send a `clear` event to Twilio to flush the audio buffer before transitioning to LISTENING

### Requirement: Handle incoming mark events
The system SHALL process incoming `mark` events from Twilio and resolve the corresponding pending mark future.

#### Scenario: Twilio sends mark confirmation
- **WHEN** a `mark` event is received from Twilio with a name matching a pending mark
- **THEN** the corresponding await SHALL be resolved, allowing the pipeline to continue

## ADDED Requirements

### Requirement: Audio loop orchestration
The system SHALL implement a `CallPipeline` class that orchestrates the full STT → ConversationAgent → TTS flow as three concurrent async tasks communicating via queues.

#### Scenario: Complete audio round-trip
- **WHEN** audio arrives from the telephony provider
- **THEN** the pipeline SHALL send it to STT, pass the transcript to Claude, synthesize the response via TTS, and send audio back to the telephony provider

#### Scenario: Streaming response
- **WHEN** Claude begins generating a response
- **THEN** TTS SHALL start synthesizing before the full response is complete (streaming text → streaming audio)

### Requirement: Call state machine
The system SHALL maintain a state machine with states: `GREETING`, `LISTENING`, `PROCESSING`, `SPEAKING`, `ENDED`. Every state transition SHALL be logged with structlog.

#### Scenario: Normal call flow
- **WHEN** a call starts
- **THEN** the state transitions SHALL follow: GREETING → LISTENING → PROCESSING → SPEAKING → LISTENING → ... → ENDED

#### Scenario: State transition logging
- **WHEN** any state transition occurs
- **THEN** the system SHALL log the transition with structlog including: previous state, new state, timestamp, and trigger reason

### Requirement: Call termination
The pipeline SHALL detect when the conversation is complete by checking `ConversationAgent.should_hangup()` on agent responses.

#### Scenario: Agent signals end of call
- **WHEN** the agent's response contains farewell phrases (e.g. "viszlát", "szép napot")
- **THEN** the pipeline SHALL transition to ENDED state and stop processing

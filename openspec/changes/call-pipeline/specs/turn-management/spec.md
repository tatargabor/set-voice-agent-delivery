## ADDED Requirements

### Requirement: End-of-speech detection
The system SHALL use Soniox endpoint detection (VAD) to determine when the customer has stopped speaking. The endpoint delay SHALL be configurable (default 1500ms).

#### Scenario: Customer finishes speaking
- **WHEN** Soniox fires an endpoint detection event (finalized tokens after silence)
- **THEN** the pipeline SHALL transition from LISTENING to PROCESSING and pass the complete transcript to Claude

#### Scenario: Customer pauses mid-sentence
- **WHEN** the customer pauses briefly but continues within the endpoint delay
- **THEN** the system SHALL wait and accumulate tokens until a true endpoint is detected

### Requirement: Barge-in handling
The system SHALL detect when the customer speaks while TTS audio is playing and immediately stop TTS output to listen.

#### Scenario: Customer interrupts agent speech
- **WHEN** STT detects speech while the pipeline is in SPEAKING state
- **THEN** the system SHALL immediately stop sending TTS audio, transition to LISTENING, and begin processing the customer's new speech

#### Scenario: Background noise during agent speech
- **WHEN** STT receives non-speech audio during SPEAKING state
- **THEN** the system SHALL NOT trigger barge-in (only confirmed speech tokens trigger it)

### Requirement: Concurrent task safety
The pipeline's three async tasks (STT loop, LLM loop, TTS loop) SHALL communicate via asyncio.Queue. The shared call state SHALL be protected by asyncio.Lock to prevent race conditions.

#### Scenario: Simultaneous state access
- **WHEN** multiple tasks attempt to read or modify the call state concurrently
- **THEN** the Lock SHALL ensure only one task modifies state at a time

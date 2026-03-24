## ADDED Requirements

### Requirement: Stream Claude responses token-by-token
The system SHALL use the Anthropic streaming API (`messages.stream()`) instead of blocking `messages.create()` to receive response tokens as they are generated.

#### Scenario: Streaming response
- **WHEN** `ConversationAgent.respond_stream()` is called
- **THEN** it SHALL yield sentence chunks as Claude generates them, not wait for the full response

### Requirement: Sentence boundary detection
The system SHALL split streaming tokens into sentence-sized chunks at natural boundaries (`. ! ?` or `,` when buffer exceeds 40 characters).

#### Scenario: Short sentence
- **WHEN** Claude generates "Igen, megkaptam."
- **THEN** the system SHALL yield "Igen, megkaptam." as one chunk after the period

#### Scenario: Long clause with comma
- **WHEN** Claude generates a clause longer than 40 characters ending with a comma
- **THEN** the system SHALL yield it as a chunk at the comma

### Requirement: First sentence latency under 1.5 seconds
The system SHALL deliver the first sentence chunk to TTS within 1.5 seconds of Claude starting to generate.

#### Scenario: Response timing
- **WHEN** a customer transcript is sent to Claude
- **THEN** the first sentence SHALL be yielded within 1.5 seconds

### Requirement: Usage tracking from stream
The system SHALL capture input_tokens and output_tokens from the streaming response after the stream completes.

#### Scenario: Token counting
- **WHEN** a streaming response finishes
- **THEN** the system SHALL report accurate input_tokens and output_tokens for metrics

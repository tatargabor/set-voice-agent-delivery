## ADDED Requirements

### Requirement: Cache control on deep response API calls
All deep response Claude API calls (streaming, tool_use, local agent) SHALL include `cache_control={"type": "ephemeral"}` to enable prompt caching on the system prompt.

#### Scenario: Streaming deep response with caching
- **WHEN** a non-research customer message triggers a streaming deep response
- **THEN** the messages.stream() call includes cache_control={"type": "ephemeral"}

#### Scenario: Tool-use deep response with caching
- **WHEN** a research question triggers the tool_use loop
- **THEN** every messages.create() call in the loop includes cache_control={"type": "ephemeral"}

#### Scenario: Local agent response with caching
- **WHEN** the local agent research path is used
- **THEN** the agent's Claude API calls include cache_control={"type": "ephemeral"}

### Requirement: Cache usage tracking
The metrics system SHALL track cache hit and cache write token counts separately from regular input tokens.

#### Scenario: Cache hit tracked
- **WHEN** a Claude API response contains cache_read_input_tokens > 0
- **THEN** the value is recorded in CallMetrics

#### Scenario: Cache write tracked
- **WHEN** a Claude API response contains cache_creation_input_tokens > 0
- **THEN** the value is recorded in CallMetrics

#### Scenario: Cache stats in call log
- **WHEN** a call ends and the log is saved
- **THEN** the log includes cache_read_input_tokens and cache_creation_input_tokens totals

### Requirement: No caching for short prompts
API calls with system prompts below the model's minimum cacheable token count SHALL NOT include cache_control to avoid unnecessary cache write costs.

#### Scenario: Fast ack skips caching
- **WHEN** the Haiku fast ack is generated with a ~100 token system prompt
- **THEN** the API call does NOT include cache_control

#### Scenario: Greeting skips caching
- **WHEN** the greeting is generated with a minimal ~200 token system prompt
- **THEN** the API call does NOT include cache_control

## MODIFIED Requirements

### Requirement: Voice-ready output
The local agent's response SHALL be max 2 sentences, suitable for TTS playback on a phone call.

#### Scenario: No markdown in voice responses
- **WHEN** Claude generates a response for voice playback
- **THEN** the system prompt SHALL instruct Claude to use plain spoken language — no markdown (`**`, `#`, `-`), no emojis, no code formatting, no URLs

#### Scenario: Outbound greeting matches call direction
- **WHEN** the agent initiates an outbound call
- **THEN** the greeting SHALL explain why we are calling (e.g., "Azért hívom, mert elkészült a projektje")
- **AND** SHALL NOT say "Miben segíthetek?" (which implies the customer called us)

#### Scenario: Inbound greeting unchanged
- **WHEN** a customer initiates an inbound call
- **THEN** the greeting SHALL remain "Miben segíthetek?" style

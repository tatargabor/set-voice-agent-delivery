## ADDED Requirements

### Requirement: Backchannel utterances do not trigger barge-in
The system SHALL ignore backchannel utterances (short acknowledgments like "mhm", "igen", "aha") during SPEAKING state instead of triggering a barge-in.

#### Scenario: Backchannel word ignored
- **WHEN** the agent is in SPEAKING state
- **AND** the STT detects a ≤2 word utterance that matches the backchannel list ("mhm", "aha", "igen", "ja", "jó", "oké", "értem", "uhum", "rendben", "persze", "naná", "hát", "ühüm", "ööö")
- **THEN** the agent continues speaking without interruption
- **AND** the utterance is logged as backchannel_ignored

#### Scenario: Stop word triggers barge-in
- **WHEN** the agent is in SPEAKING state
- **AND** the STT detects a ≤2 word utterance containing a stop word ("nem", "stop", "várj", "de", "figyelj", "halló", "hé")
- **THEN** the system triggers a barge-in as before (TTS stops, transition to LISTENING)

#### Scenario: Multi-word utterance triggers barge-in
- **WHEN** the agent is in SPEAKING state
- **AND** the STT detects a 3+ word utterance
- **THEN** the system triggers a barge-in regardless of content

#### Scenario: Unknown short utterance ignored
- **WHEN** the agent is in SPEAKING state
- **AND** the STT detects a ≤2 word utterance that is NOT in the backchannel list AND NOT in the stop list
- **THEN** the agent continues speaking (treat as noise/fragment)
- **AND** the utterance is logged as unknown_short_ignored

### Requirement: Text normalization before classification
The system SHALL normalize STT text before backchannel classification by lowercasing, stripping whitespace, and removing punctuation.

#### Scenario: Punctuated backchannel recognized
- **WHEN** the STT returns "Igen." or "Oké!"
- **THEN** the normalized form "igen" or "oké" matches the backchannel list

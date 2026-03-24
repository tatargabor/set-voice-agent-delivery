## ADDED Requirements

### Requirement: CLI entry point for outbound calls
The system SHALL provide a CLI command that orchestrates the full outbound call lifecycle: load script → safety checks → start server → place call → run pipeline → hangup → print transcript.

#### Scenario: Successful outbound call
- **WHEN** the user runs `python -m src.call_runner --script website_followup --phone "+36..." --customer-name "..." --company-name "..." --website-url "..."`
- **THEN** the system SHALL execute the full call lifecycle and print the transcript at the end

#### Scenario: Safety check fails
- **WHEN** the CLI is invoked but a safety check fails (DNC or legal hours)
- **THEN** the system SHALL print the failure reason and exit without placing a call

### Requirement: GDPR recording notice
The system SHALL inform the customer that the call may be recorded, as part of the greeting or immediately after.

#### Scenario: Recording notice delivered
- **WHEN** the call connects and the agent greets the customer
- **THEN** the system SHALL include a recording notice in Hungarian (e.g. "A hívás rögzítésre kerülhet")

### Requirement: Transcript output
The system SHALL print the full conversation transcript after the call ends.

#### Scenario: Call completed normally
- **WHEN** the call ends (agent or customer hangs up)
- **THEN** the system SHALL output the complete transcript showing each turn (Agent/Customer) with timestamps

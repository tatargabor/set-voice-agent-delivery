## ADDED Requirements

### Requirement: Write JSON log file per call
The system SHALL write one JSON file per completed call to `logs/calls/YYYY-MM-DD/` containing metadata, transcript, costs, performance, and errors.

#### Scenario: Successful call logged
- **WHEN** a call completes (any outcome)
- **THEN** a JSON file SHALL be created at `logs/calls/{date}/{call_sid_short}_{customer_slug}_{HH-MM}.json`

#### Scenario: Log file content structure
- **WHEN** a log file is written
- **THEN** it SHALL contain: `call_id`, `timestamp_start`, `timestamp_end`, `duration_sec`, `phone_masked`, `customer_name`, `script`, `outcome`, `transcript[]`, `cost{}`, `performance{}`, `errors[]`

### Requirement: Log directory auto-creation
The system SHALL create the date subdirectory automatically if it doesn't exist.

#### Scenario: First call of the day
- **WHEN** a call is logged and `logs/calls/2026-03-24/` doesn't exist
- **THEN** the directory SHALL be created automatically

### Requirement: Outcome classification
The system SHALL classify each call outcome as one of: `completed`, `dropped`, `error`, `dnc`.

#### Scenario: Normal call completion
- **WHEN** the agent says farewell and the call ends normally
- **THEN** outcome SHALL be `completed`

#### Scenario: Call error
- **WHEN** the pipeline encounters an error during the call
- **THEN** outcome SHALL be `error` and the error details SHALL be in the `errors` array

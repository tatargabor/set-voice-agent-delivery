## ADDED Requirements

### Requirement: Do Not Call list enforcement
The system SHALL check every phone number against a DNC list before placing a call. The DNC list SHALL be stored as a local text file (`data/dnc.txt`), one number per line.

#### Scenario: Number is on DNC list
- **WHEN** `pre_call_check(phone)` is called and the number is in `data/dnc.txt`
- **THEN** the system SHALL refuse to place the call and raise an error

#### Scenario: Number is not on DNC list
- **WHEN** `pre_call_check(phone)` is called and the number is not in the list
- **THEN** the check SHALL pass

#### Scenario: Customer requests DNC during call
- **WHEN** the customer says "ne hívjatok" or similar opt-out phrase during a call
- **THEN** the system SHALL add their number to `data/dnc.txt`

### Requirement: Legal hours enforcement
The system SHALL only place calls between 08:00 and 20:00 local time.

#### Scenario: Call within legal hours
- **WHEN** a call is attempted at 14:00 local time
- **THEN** the check SHALL pass

#### Scenario: Call outside legal hours
- **WHEN** a call is attempted at 06:30 local time
- **THEN** the system SHALL refuse to place the call and raise an error with the allowed time window

### Requirement: Pre-call safety gate
The system SHALL run all safety checks (DNC + legal hours) as a single `pre_call_check()` before every outbound call. No call SHALL be placed if any check fails.

#### Scenario: All checks pass
- **WHEN** the number is not on DNC and the time is within legal hours
- **THEN** the call SHALL proceed

#### Scenario: Any check fails
- **WHEN** any safety check fails
- **THEN** the system SHALL NOT place the call and SHALL log the reason

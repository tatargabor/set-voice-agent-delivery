## ADDED Requirements

### Requirement: Immediate acknowledgment via fast model
The system SHALL generate an immediate acknowledgment using Claude Haiku within ~300ms of receiving customer speech.

#### Scenario: Customer asks a question
- **WHEN** the customer says "szeretnék zöld menüt"
- **THEN** the system SHALL immediately respond with a natural ack like "Értem, megnézem!" before the deep analysis starts

### Requirement: Fast ack is non-committal
The fast acknowledgment SHALL only acknowledge receipt, never commit to an action or answer.

#### Scenario: Ack content
- **WHEN** a fast ack is generated
- **THEN** it SHALL be a short acknowledgment (e.g. "Értem", "Rendben, megnézem", "Jó kérdés") — never "Igen, megcsináljuk" or other commitments

### Requirement: Skip fast ack for simple exchanges
The system SHALL skip the fast ack layer for short/simple customer messages (greetings, farewells, yes/no answers).

#### Scenario: Simple greeting
- **WHEN** the customer says "Szia" or "Igen"
- **THEN** the system SHALL skip the fast ack and go directly to the response

## ADDED Requirements

### Requirement: Central config file
The system SHALL load application settings from `config.yaml` at startup, with sensible defaults if the file is missing. API keys SHALL remain in `.env`.

#### Scenario: Config loaded at startup
- **WHEN** the server starts with a valid `config.yaml`
- **THEN** the system SHALL use the configured values for models, voice settings, research mode, and projects_dir

#### Scenario: Missing config file
- **WHEN** `config.yaml` does not exist
- **THEN** the system SHALL use default values (tool_use mode, standard model names, etc.)

### Requirement: Research mode configuration
The system SHALL support `research.mode` in `config.yaml` with values: `tool_use`, `local_agent`, or `auto`.

#### Scenario: Default mode
- **WHEN** `research.mode` is not set
- **THEN** the system SHALL use `tool_use` mode (backward compatible)

#### Scenario: Local agent mode
- **WHEN** `research.mode` is set to `local_agent`
- **THEN** all non-simple questions SHALL be routed to the local agent

#### Scenario: Auto mode routing
- **WHEN** `research.mode` is set to `auto` and the customer asks a research question (containing keywords like "fájl", "kód", "spec", "change", "keress", "nézd meg")
- **THEN** the system SHALL route to the local agent
- **AND** simple/conversational questions SHALL use tool_use

### Requirement: Mode logged per call
The research mode used SHALL be logged in the call metrics for cost comparison.

#### Scenario: Mode in call log
- **WHEN** a call completes
- **THEN** the call log SHALL include `research_mode` field with the mode used

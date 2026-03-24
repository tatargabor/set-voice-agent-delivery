## ADDED Requirements

### Requirement: Load project data from local directory
The system SHALL load project context from a local directory specified in the call script YAML `project_dir` field.

#### Scenario: Project directory exists
- **WHEN** `project_dir` is set and the directory exists
- **THEN** the system SHALL load: README/CLAUDE.md summary, openspec specs overview, active changes list, design snapshot (if exists)

#### Scenario: Project directory not set
- **WHEN** `project_dir` is not set in the call script
- **THEN** the system SHALL proceed without project context (backward compatible)

### Requirement: Load previous call log
The system SHALL search `logs/calls/` for the most recent call log matching the customer name and include the transcript summary.

#### Scenario: Previous call exists
- **WHEN** a call log for this customer exists in logs/calls/
- **THEN** the previous call transcript SHALL be included in the project context

#### Scenario: No previous call
- **WHEN** no matching call log exists
- **THEN** the system SHALL proceed without previous call context

### Requirement: Context size limit
The total project context injected into the system prompt SHALL NOT exceed 4000 characters.

#### Scenario: Large project
- **WHEN** the combined project data exceeds 4000 characters
- **THEN** the system SHALL truncate to the most important sections (summary first, then specs, then changes)

### Requirement: Inject context into system prompt
The loaded project context SHALL be appended to the Claude system prompt so the agent can reference project specifics.

#### Scenario: Agent uses context
- **WHEN** the customer asks "what color is my menu?"
- **THEN** the agent SHALL be able to answer from the loaded project context

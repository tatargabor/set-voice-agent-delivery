## ADDED Requirements

### Requirement: Project index generation via Claude Haiku
The system SHALL generate a structured project summary by reading all docs/*.md and openspec/ files from a customer project directory and summarizing them with Claude Haiku into a fixed-structure output.

#### Scenario: Successful index generation
- **WHEN** the indexer receives a valid project_id that resolves to an existing project directory
- **THEN** the system reads all .md files from docs/, all spec.md files from openspec/specs/, all proposal.md and tasks.md from openspec/changes/, and the design-snapshot.md if present
- **AND** sends the combined content to Claude Haiku with a structured prompt
- **AND** returns a JSON object with fields: project_name, description, modules, design, status, previous_requests

#### Scenario: Project directory does not exist
- **WHEN** the indexer receives a project_id that does not resolve to a valid directory
- **THEN** the system returns an error indicating the project was not found

#### Scenario: Content exceeds Haiku context
- **WHEN** the combined raw content exceeds 30000 characters
- **THEN** the system truncates the least important sections (previous call logs first, then older changes) before sending to Haiku

### Requirement: Widget-triggered indexing endpoint
The system SHALL expose a POST /api/index-project endpoint that accepts a project_id and triggers background index generation.

#### Scenario: Index triggered from widget
- **WHEN** the widget sends POST /api/index-project with {"project": "my-project"}
- **THEN** the endpoint responds immediately with {"status": "indexing"} (HTTP 202)
- **AND** the index generation runs asynchronously in the background

#### Scenario: Index already cached and fresh
- **WHEN** the widget sends POST /api/index-project for a project whose index cache is still valid
- **THEN** the endpoint responds with {"status": "cached"} (HTTP 200) without regenerating

### Requirement: Structured summary format
The system SHALL produce summaries following a fixed structure so the voice agent receives consistent project context.

#### Scenario: Summary contains all sections
- **WHEN** a project has docs, specs, changes, and design data
- **THEN** the summary contains: project_name, description, modules (list with brief descriptions), design (colors, font, style), status (done/in-progress/planned items), and previous_requests (from call logs)

#### Scenario: Missing sections produce empty values
- **WHEN** a project has no docs/ directory
- **THEN** the summary contains an empty string for the relevant section, not an error

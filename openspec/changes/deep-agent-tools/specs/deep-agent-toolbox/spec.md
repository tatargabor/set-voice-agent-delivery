## ADDED Requirements

### Requirement: File read tool
The Deep Layer SHALL have a `file_read` tool to read files from the customer's project directory.

#### Scenario: Read a file
- **WHEN** Claude calls `file_read(path="src/components/Navbar.tsx")`
- **THEN** the system SHALL return the file contents (max 2000 chars), resolved relative to project_dir

### Requirement: Grep search tool
The Deep Layer SHALL have a `grep_search` tool to search for patterns in the project.

#### Scenario: Search code
- **WHEN** Claude calls `grep_search(pattern="menu", path="src/")`
- **THEN** the system SHALL return matching lines with file paths

### Requirement: OpenSpec read tool
The Deep Layer SHALL have an `openspec_read` tool to read specs or changes.

#### Scenario: Read a spec
- **WHEN** Claude calls `openspec_read(name="navbar")`
- **THEN** the system SHALL return the spec content from openspec/specs/navbar/spec.md

### Requirement: OpenSpec create change tool
The Deep Layer SHALL have an `openspec_create_change` tool to create work items from customer requests.

#### Scenario: Create change during call
- **WHEN** Claude calls `openspec_create_change(name="green-menu", description="Change menu color to green")`
- **THEN** the system SHALL create a new openspec change and confirm to the customer

### Requirement: Design check tool
The Deep Layer SHALL have a `design_check` tool to look up component design tokens.

#### Scenario: Check design
- **WHEN** Claude calls `design_check(component="Navbar")`
- **THEN** the system SHALL return the relevant design tokens from design-snapshot.md

### Requirement: Sandboxed tool execution
All tool file operations SHALL be sandboxed to the customer's project_dir. Absolute paths and directory traversal (`..`) SHALL be rejected.

#### Scenario: Path traversal attempt
- **WHEN** a tool call includes `../../etc/passwd`
- **THEN** the system SHALL reject it with an error

### Requirement: Tool execution timeout
The total tool_use loop SHALL complete within 15 seconds.

#### Scenario: Slow tool execution
- **WHEN** tool execution exceeds 15 seconds total
- **THEN** the system SHALL return the best available partial answer

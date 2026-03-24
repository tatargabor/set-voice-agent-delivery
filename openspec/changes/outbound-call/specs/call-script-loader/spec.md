## ADDED Requirements

### Requirement: Parse YAML call scripts
The system SHALL load call script YAML files from `call_scripts/` and produce a validated `CallContext` object with all required fields.

#### Scenario: Valid call script
- **WHEN** a valid YAML file (e.g. `website_followup.yaml`) is loaded with customer variables
- **THEN** the system SHALL return a `CallContext` with customer_name, company_name, purpose, and optional fields populated

#### Scenario: Missing required field
- **WHEN** a YAML file is missing a required field (e.g. `purpose`)
- **THEN** the system SHALL raise a validation error listing the missing field

### Requirement: Variable substitution
The system SHALL substitute variables defined in the script's `context.variables` list with values provided at runtime (CLI args or contacts data).

#### Scenario: All variables provided
- **WHEN** the script defines variables `[customer_name, company_name, website_url]` and all are provided
- **THEN** the system prompt and context SHALL have all placeholders replaced with actual values

#### Scenario: Missing variable
- **WHEN** a required variable is not provided at runtime
- **THEN** the system SHALL raise an error listing the missing variable

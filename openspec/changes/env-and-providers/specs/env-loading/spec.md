## ADDED Requirements

### Requirement: Load environment variables from .env file
The system SHALL load environment variables from a `.env` file in the project root using python-dotenv. Variables already set in the environment SHALL NOT be overwritten.

#### Scenario: .env file exists with all keys
- **WHEN** the application starts and a `.env` file exists with all required keys
- **THEN** all keys are loaded into the environment and available via `os.environ`

#### Scenario: .env file does not exist
- **WHEN** the application starts and no `.env` file exists
- **THEN** the system SHALL proceed without error (keys may be set via environment directly)

### Requirement: Validate required environment variables
The system SHALL validate that required environment variables are present at startup. Validation SHALL be per-provider: only keys needed by active providers are required.

#### Scenario: All required keys present
- **WHEN** `validate_config()` is called with provider names
- **THEN** validation passes and returns a config object with all values

#### Scenario: Missing required key
- **WHEN** `validate_config()` is called and a required key is missing
- **THEN** the system SHALL raise a clear error listing all missing keys (not just the first one)

#### Scenario: Provider-specific validation
- **WHEN** only STT provider is requested
- **THEN** only `SONIOX_API_KEY` and `ANTHROPIC_API_KEY` are required (Twilio/Google keys are not checked)

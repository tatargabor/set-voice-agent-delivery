## ADDED Requirements

### Requirement: File-based index cache with mtime invalidation
The system SHALL cache generated project indexes as JSON files at logs/indexes/<project_id>.json, including source file mtimes for invalidation.

#### Scenario: Cache hit with fresh data
- **WHEN** load_project_context is called for a project that has a cached index
- **AND** none of the source files (docs/*.md, openspec/**/*.md) have been modified since the cache was written
- **THEN** the system uses the cached summary instead of loading raw files

#### Scenario: Cache miss triggers raw fallback
- **WHEN** load_project_context is called for a project with no cached index
- **THEN** the system falls back to the current raw file loading behavior (no error, seamless fallback)

#### Scenario: Cache invalidation on file change
- **WHEN** any source file's mtime is newer than the cached index timestamp
- **THEN** the cache is considered stale and the system falls back to raw loading
- **AND** the next /api/index-project call regenerates the index

### Requirement: Cache structure
The cache JSON SHALL contain the summary, source file mtimes, and generation metadata.

#### Scenario: Cache file contents
- **WHEN** an index is generated and saved
- **THEN** the JSON file contains: summary (the structured text), generated_at (ISO timestamp), source_files (dict of relative_path → mtime), and model (the Claude model used)

## ADDED Requirements

### Requirement: Local agent research function
The system SHALL provide an async `research()` function that takes a question, project_dir, and cache, then autonomously investigates the project and returns a concise voice-ready answer.

#### Scenario: Simple project question
- **WHEN** the agent receives question "Milyen change-ek vannak nyitva?" with a valid project_dir
- **THEN** the agent SHALL use openspec_read and return a max 2-sentence summary of active changes

#### Scenario: Code investigation question
- **WHEN** the agent receives question "Milyen színű a navbar?" with a valid project_dir
- **THEN** the agent SHALL use file_read/grep_search to find the answer and return a concise response

### Requirement: Agent uses existing tools
The local agent SHALL reuse the same tool definitions from `agent_tools.py` (file_read, grep_search, openspec_read, design_check) with the same sandboxing.

#### Scenario: Tool reuse
- **WHEN** the local agent needs to read a file
- **THEN** it SHALL use the same `execute_tool()` function as the tool_use path

### Requirement: Agent timeout
The local agent SHALL complete within 10 seconds total. If exceeded, it SHALL return the best available partial answer.

#### Scenario: Timeout
- **WHEN** agent research exceeds 10 seconds
- **THEN** the system SHALL return "Sajnos nem sikerült időben megtalálni az információt."

### Requirement: Agent max iterations
The local agent SHALL perform at most 3 tool call iterations before returning a final answer.

#### Scenario: Max iterations reached
- **WHEN** the agent has performed 3 tool iterations without a final text response
- **THEN** the agent SHALL synthesize an answer from the collected tool results

### Requirement: Context cache
The system SHALL maintain an in-memory per-project cache that persists between calls within the same server process.

#### Scenario: First call indexes project
- **WHEN** the first call arrives for a project with no cache
- **THEN** the system SHALL populate file_index and spec_summaries before answering

#### Scenario: Subsequent call uses cache
- **WHEN** a second call arrives for the same project
- **THEN** the system SHALL reuse the cached file_index and spec_summaries without re-indexing

#### Scenario: Cache includes findings
- **WHEN** the agent discovers a key finding (e.g., "navbar color is #2563EB")
- **THEN** the finding SHALL be added to the cache for future questions

### Requirement: Voice-ready output
The local agent's response SHALL be max 2 sentences, suitable for TTS playback on a phone call.

#### Scenario: Long answer truncation
- **WHEN** the agent generates a response longer than 3 sentences
- **THEN** the system SHALL truncate to 3 sentences and append "Szeretnéd, hogy részletesebben elmondjam?"

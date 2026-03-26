## 1. Project Indexer Core

- [x] 1.1 Create `src/project_indexer.py` — `generate_index(project_dir, project_id)` function that reads all docs/*.md and openspec/**/*.md files, sends to Claude Haiku with structured prompt, returns summary dict
- [x] 1.2 Implement structured prompt for Haiku — fixed output format: project_name, description, modules, design, status, previous_requests
- [x] 1.3 Handle content truncation — if combined raw content >30k chars, drop least important sections (old call logs first, then older changes)
- [x] 1.4 Load previous call log summaries into the index (from logs/summaries/)

## 2. Cache Layer

- [x] 2.1 Implement cache write — save index to `logs/indexes/<project_id>.json` with summary, generated_at, source_files mtimes, model
- [x] 2.2 Implement cache read + mtime validation — compare each source file mtime against cached value, return None if stale
- [x] 2.3 Integrate cache into `project_context.py` — `load_project_context()` checks cache first, falls back to raw loading if no cache or stale

## 3. API Endpoint

- [x] 3.1 Add `POST /api/index-project` endpoint to webhook.py — accepts `{"project": "id"}`, triggers async background indexing
- [x] 3.2 Return `{"status": "cached"}` (200) if cache is fresh, `{"status": "indexing"}` (202) if generation starts
- [x] 3.3 Handle errors (invalid project, missing dir) with appropriate HTTP responses

## 4. Widget Integration

- [x] 4.1 Add onChange handler to project dropdown in voice-widget.html — POST to /api/index-project on selection
- [x] 4.2 Show brief loading indicator while indexing (optional, non-blocking)

## 5. Testing

- [x] 5.1 Unit test: index generation with mock project directory (docs + openspec files)
- [x] 5.2 Unit test: cache hit/miss/invalidation logic
- [x] 5.3 Integration test: /api/index-project endpoint returns correct status codes

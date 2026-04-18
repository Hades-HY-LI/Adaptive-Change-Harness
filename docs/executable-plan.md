# Executable Plan

## Product Name

Adaptive Change Harness

Short demo label:
Break-Fix-Ship

## Product Thesis

Build an adaptive verification and repair harness for code changes.
The system should compound with stronger LLMs rather than get replaced by them.
The durable product value lives in:
- change orchestration
- evaluator design
- repo-specific invariants
- repeatable evidence collection
- safe or unsafe merge decisions

## User Story

A developer submits a code change, or the harness injects a controlled break into a known codebase.
The system runs evaluators, finds a verifiable failure, diagnoses root cause, proposes and applies a patch, reruns evaluators, and emits an evidence packet showing whether the change is safe to merge.

## V1 Scope

V1 must stay narrow and demoable.
It should support exactly three failure families:
- logic regression
- contract violation
- invariant or pattern violation

V1 should not try to solve:
- full architecture review
- open-ended system design critique
- multi-repo analysis
- arbitrary language support
- enterprise auth or team workflows

## Stack

### Frontend
- React 18+
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query
- Zustand only if local state becomes messy
- Monaco diff viewer or CodeMirror diff if needed

### Backend
- Python 3.12
- FastAPI
- Pydantic
- SQLModel or direct SQLite access with a minimal repository layer
- httpx for provider calls
- pytest for backend tests

### Persistence And Artifacts
- SQLite for run metadata
- local filesystem artifact store for:
  - evaluator logs
  - test stdout and stderr
  - model prompts and responses
  - generated patches
  - final evidence packet

### LLM Providers
- OpenAI adapter
- provider interface from day one so Anthropic and other providers can be added later

V1 requirement:
- OpenAI support is required
- Anthropic support is deferred and optional

## Repository Shape

```text
apps/
  api/
    app/
      api/
      core/
      models/
      providers/
      evaluators/
      services/
      storage/
    tests/
  web/
    src/
      app/
      components/
      features/
      lib/
      styles/
demo-repo/
artifacts/
docs/
skills/
```

## Frontend Plan

### Primary Screens
1. Run Dashboard
   - shows recent runs
   - create run button
   - provider and model selector
   - break type selector

2. Run Detail
   - status timeline
   - evaluator panel
   - root cause summary
   - patch diff
   - final merge-confidence card

3. Evidence Drawer
   - prompt and response excerpts
   - logs
   - stacktrace
   - invariant failures

### UX Rules
- the first screen must answer "what broke, why, what changed, is it safe now"
- the diff and evaluator status should be visible without scrolling through prose
- use streaming updates for run progress
- preserve a clean demo mode with seeded data and deterministic ordering

## Backend Plan

### Core Services
1. Run Orchestrator
   - creates run record
   - checks out or copies demo repo workspace
   - dispatches break step
   - dispatches evaluator step
   - dispatches diagnosis and repair step
   - reruns evaluators
   - writes final evidence packet

2. Break Engine
   - controlled mutators for each failure family
   - deterministic seeds for replay

3. Evaluator Engine
   - test runner
   - contract checker
   - invariant checker

4. Provider Gateway
   - wraps OpenAI in V1
   - leaves a stable adapter boundary for Anthropic later
   - normalizes model output into diagnosis and patch response shapes

5. Patch Service
   - validates patch shape
   - applies patch
   - snapshots before and after state

6. Evidence Service
   - stores prompts, diffs, logs, and verdicts

### API Surface

#### `POST /api/v1/runs`
Create a run.
Request fields:
- `mode`: `inject` or `verify`
- `break_type`: `logic_regression | contract_violation | invariant_violation`
- `provider`: `openai | anthropic`
  - in V1, `openai` is the only enabled provider unless later configured
- `model`: string
- `target_ref`: optional demo repo snapshot id
- `seed`: optional integer

#### `GET /api/v1/runs`
List runs for the dashboard.

#### `GET /api/v1/runs/{run_id}`
Return run summary, current state, and evidence references.

#### `GET /api/v1/runs/{run_id}/events`
Server-sent events stream for timeline updates.

#### `POST /api/v1/runs/{run_id}/retry`
Retry the same run with a different provider or model.

#### `GET /api/v1/providers`
Return enabled providers and available configured models.

#### `GET /api/v1/health`
Health endpoint for deployment.

## Data Model

### Run
- id
- created_at
- mode
- break_type
- provider
- model
- seed
- status
- verdict
- demo_repo_revision

### Run Event
- id
- run_id
- type
- stage
- summary
- created_at
- artifact_path

### Evidence Packet
- run_id
- failed_evaluators_before
- passed_evaluators_after
- root_cause_summary
- patch_summary
- merge_confidence
- artifact_manifest

## Evaluators

### Logic Regression
- run pytest against deterministic unit tests
- capture failing test names and traceback

### Contract Violation
- validate structured output or API response shape against a schema fixture
- capture contract diff

### Invariant Violation
- enforce repo-level rules such as:
  - all public handlers return the standard response wrapper
  - all writes go through a service function
  - all error responses include code and message

## Demo Repo

Create a small but believable demo repo inside `demo-repo/`.
Recommended shape:
- tiny service domain such as order pricing, coupon handling, or subscription billing
- 6 to 10 deterministic tests
- at least 3 invariant checks
- one API-like entrypoint and one service layer

The repo should be simple enough to understand in 30 seconds and rich enough to support the three failure families.

## Execution Flow

1. user creates a run
2. backend clones or copies the clean demo repo snapshot into a temp workspace
3. backend injects or accepts a broken change
4. evaluator engine runs and records failure
5. provider gateway builds diagnosis and patch request
6. patch service applies returned patch
7. evaluator engine reruns
8. backend writes evidence packet and verdict
9. frontend shows final diff and merge confidence

## Delivery Sequence

### Phase 0: Foundation
- scaffold monorepo folders
- setup Python backend and React frontend
- add lint, format, and test commands
- add `.env.example` files

### Phase 1: Harness Core
- create demo repo
- implement run model and SQLite persistence
- implement break engine with seeded mutations
- implement evaluator engine

### Phase 2: Model Repair Loop
- add OpenAI adapter
- create diagnosis prompt
- create patch prompt
- implement patch validation and apply flow

Optional later extension:
- add Anthropic adapter through the same provider interface

### Phase 3: Frontend Demo
- build dashboard and run detail screen
- stream run events
- add diff and evaluator cards

### Phase 4: Deployment And Polish
- deploy web to Vercel
- deploy API to Render
- configure CORS, secrets, and health checks
- seed a canned demo run for backup

## Future-Proofing Rules

The system must be able to absorb future model jumps.
Design for that now by keeping these boundaries:
- provider adapters must be isolated
- evaluators must be deterministic and versioned
- artifact format must be stable across providers
- prompts must be stored and attributable per run
- no UI language should assume one provider is the product

## Success Criteria

V1 is done when:
- one click creates a run
- at least one break family reliably fails an evaluator
- at least one provider can repair the failure end-to-end
- the UI shows evidence and diff clearly
- a judge can understand the story in under 90 seconds

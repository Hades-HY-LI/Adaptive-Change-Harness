# Conventions

## Product Conventions

### Canonical Terms
- Harness: the whole product
- Run: one execution of break, evaluate, repair, validate
- Break: a verifiable failure introduced or detected by the system
- Evaluator: deterministic check that passes or fails
- Evidence Packet: final artifact bundle proving why a run is safe or unsafe
- Verdict: `safe`, `unsafe`, or `needs_review`
- Repo Profile: detected metadata about an ingested repo
- Failure Case: a reproducible discovered failure with exact repro steps
- Repair Skill: a reusable bug-repair asset created or updated from validated cases
- Skill Assets: the persistent store of product-generated repair skills under `skill_assets/`

### Scope Rules
- V1 break classes are limited to logic regression, contract violation, and invariant violation.
- Architecture critique and system-design critique are advisory only in V1.
- Every new feature proposal must map back to one of the required hackathon tracks.
- V2 should stay focused on Python service repos with runnable tests or clear entrypoints.
- The evolving skill system must strengthen discovery, repair, and replay; it must not turn the product into a generic agent platform.

## Backend Conventions

### General
- Python 3.12+
- Full type hints on non-trivial functions
- Pydantic models at every API boundary
- No provider-specific logic outside `providers/`
- No direct shell command execution from route handlers; use service functions

### File Layout
- `api/`: route declarations only
- `services/`: orchestration and business logic
- `providers/`: OpenAI and Anthropic adapters
- `evaluators/`: deterministic checks only
- `storage/`: DB and artifact persistence only
- `skill_assets/`: persistent product-generated repair skills and revisions
- `skills/`: repo-local Codex/operator skills only; do not mix product-generated repair skills into this directory

### Error Handling
- Never swallow shell or provider errors
- Normalize external errors into structured app errors
- Every failed run stage must emit a run event and artifact reference

### Patch Safety
- Only apply textual patches after validation
- Store the raw model output before normalization
- Store pre-patch and post-patch file snapshots
- Never mark a patch safe if deterministic evaluators still fail
- Never promote a repair into a reusable skill unless deterministic validation passes after the patch

### Shell Execution
- All commands must have:
  - explicit working directory
  - timeout
  - stdout and stderr capture
  - exit code recording
- Prefer subprocess wrappers over inline shell strings where possible
- No destructive commands outside the temp workspace
- Discovery probes and generated tests must run inside isolated workspaces only

## API Conventions

### Versioning
- Prefix all HTTP endpoints with `/api/v1`
- Breaking changes require a new version prefix

### Payload Rules
- Requests and responses use snake_case on the backend
- Frontend client may map to camelCase locally, but wire format stays snake_case
- Use stable enum strings for status, break type, and verdict values

### Streaming
- Use server-sent events for run updates in V1
- Event types should be explicit, such as:
  - `run_created`
  - `break_applied`
  - `evaluation_failed`
  - `diagnosis_ready`
  - `patch_applied`
  - `evaluation_passed`
  - `verdict_ready`
- V2 should add explicit events for:
  - `codebase_profiled`
  - `discovery_started`
  - `failure_case_captured`
  - `skill_matched`
  - `skill_created`
  - `skill_updated`

## Frontend Conventions

### Architecture
- Feature-first organization under `src/features/`
- Presentational components stay dumb when possible
- API fetching lives in `src/lib/api/` or feature hooks
- Keep one source of truth for run state per screen

### Design Direction
The UI should feel like a verification war room, not a chatbot.

Use:
- strong typography
- high-contrast status colors
- dense but readable information layout
- visible logs, diffs, and evaluator states

Avoid:
- generic AI chat bubbles
- purple gradients on white backgrounds
- empty marketing-style hero pages
- soft, low-information dashboards
- hiding skill reuse or skill creation in secondary settings panels

### Typography
- Headings: Space Grotesk
- Body: IBM Plex Sans
- Code and logs: IBM Plex Mono

### Color Tokens
- background: near-black graphite
- surface: dark slate or warm stone
- text: soft off-white
- success: acid green
- warning: amber
- failure: hot red
- accent: steel blue

### Motion
- Use motion to reveal stage progression and diff updates
- Keep animations short and functional
- No decorative motion during critical status transitions

## Design System Rules

### Core Components
- Run timeline
- Evaluator result card
- Root cause summary card
- Diff viewer panel
- Merge confidence card
- Artifact drawer

### Component Behavior
- Status should always be visible without opening a modal
- A user should not need to read prose to know whether the run is safe
- Diff and evaluator outputs take priority over model explanation text

## Prompt And Model Conventions

### Provider Independence
- Prompt templates must not depend on provider-specific response quirks
- Normalize provider outputs into internal response objects
- Keep prompts in versioned files or constants with clear names

### Prompt Rules
- Ask for grounded diagnosis tied to failing evaluator evidence
- Ask for minimal patches instead of broad rewrites
- Always include the exact failing signals in the repair request
- Capture model name, provider, and prompt version on every run

### Skill Rules
- A repair skill must be stored as structured data plus concise executable guidance, not as an opaque text blob only.
- Skill matching should use explicit bug signals and failure metadata first; semantic similarity may assist but should not be the sole decision path.
- Every skill update must create a new revision with lineage to the triggering failure case.
- If a matched skill was helpful but insufficient, update that skill instead of silently bypassing it.
- If no existing skill adequately matches, create a new skill after a validated fix.
- Generated tests or evaluators may inform a repair, but they must be materialized and rerun deterministically before they can affect verdicts or skill promotion.

## Testing Conventions

### Backend
- Unit test each evaluator
- Unit test provider response normalization
- Integration test the full run flow against a fake provider before relying on live models
- Unit test skill matching, skill creation, and skill revision logic
- Integration test discover -> repair -> learn -> replay flows against a fake provider before relying on live models

### Frontend
- Component tests for status rendering and evidence cards
- End-to-end happy path with Playwright once the UI is stable

## Git And Review Conventions

- Keep PRs small and stageable
- Separate infrastructure changes from feature behavior changes when practical
- Include screenshots or terminal output for user-facing behavior changes
- If a change affects the run lifecycle, update docs in the same PR

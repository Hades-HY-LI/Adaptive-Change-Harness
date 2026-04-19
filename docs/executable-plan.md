# Executable Plan

## Product Name

Adaptive Change Harness

Short demo label:
Break-Fix-Learn

## Product Thesis

Build an adaptive verification, repair, and learning harness for codebases.
The system should compound with stronger LLMs rather than get replaced by them.
The durable product value lives in:
- codebase intake and profiling
- failure discovery and reproduction
- deterministic validation and evidence collection
- repair orchestration
- evolving repair skills that are created, reused, and improved over time

The harness is not a generic agent platform.
It is a code-change and codebase verification system whose learning loop is anchored to reproducible failures and deterministic evidence.

## User Story

A developer uploads a real Python service repo.
The harness profiles it, discovers a real latent failure without mutating source first, reproduces it, diagnoses root cause, proposes and applies a patch, reruns deterministic checks, emits an evidence packet, and then stores or updates a reusable repair skill for similar failures.

## Product Modes

### Discover
- primary V2 mode
- ingest an external repo
- find a real failure without mutating source first
- reproduce, repair, validate, and learn from the case

### Inject
- fallback demo mode
- keep controlled seeded failures for deterministic demos and regression testing of the harness itself

### Replay
- rerun a saved failure case
- validate that the failure still reproduces
- re-attempt repair with current models and current skill assets

## Scope

### V2 Target
- Python 3.12+ service repos
- FastAPI or similarly obvious Python service layouts
- small to medium repos
- repos with runnable tests or clear entrypoints

### Do Not Target In V2
- arbitrary language support
- large monorepos with complex infra
- enterprise auth and permissions workflows
- broad architecture review
- generic chatbot behavior

## Learning System Thesis

The evolving part of the product is a persistent repair-skill library.
Every validated repair should either:
- create a new repair skill when the failure is not covered
- reuse an existing repair skill when it matches well
- update an existing repair skill when the match was correct but the flow was incomplete

These skills are core product assets.
They must live in an isolated, durable store that the harness can read at runtime and grow over time.

Important repo distinction:
- `skills/` remains reserved for Codex/operator skills used by developers working on this repo
- product-generated repair skills live in `skill_assets/`

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
- SQLite for run metadata and indexes
- local filesystem artifact store for:
  - evaluator logs
  - probe outputs
  - test stdout and stderr
  - model prompts and responses
  - generated patches
  - failure-case packets
  - final evidence packets
- persistent `skill_assets/` store for learned repair skills and revisions

### LLM Providers
- OpenAI adapter from day one
- provider interface from day one so other providers can be added later

V2 requirement:
- OpenAI support is required
- do not block V2 on Anthropic or other providers

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
artifacts/
demo-repo/                      # V1 fallback only
docs/
skill_assets/
  manifests/
  skills/
  revisions/
  indexes/
skills/                         # repo-local Codex/operator skills, not product output
```

Separate V2 demo target repo:
- create outside this harness repo
- suggested name: `adaptive-harness-demo-billing`

## Frontend Plan

### Primary Screens
1. Codebase Intake
   - zip upload
   - mode selector
   - provider and model selector

2. Repo Profile
   - detected language, framework, commands, and entrypoints
   - risk areas and discovery plan

3. Discovery Console
   - baseline run status
   - active probes
   - live findings and ranking

4. Failure Case
   - exact repro
   - failing command and output
   - suspect files and confidence

5. Repair Console
   - selected skill or no-match decision
   - diagnosis summary
   - patch diff
   - retest results
   - merge confidence

6. Skill Library View
   - learned skills
   - created or updated skill after a run
   - reuse history and success rate

### UX Rules
- the first screen after a run starts must answer:
  - what failed
  - how it was reproduced
  - whether an existing skill matched
  - what changed
  - whether it is safe now
- the UI should show skill reuse or skill creation as part of the main run story, not as a hidden admin detail
- preserve inject mode as a backup demo path

## Backend Plan

### Core Services
1. Run Orchestrator
   - creates run record
   - dispatches discover, inject, or replay flow
   - coordinates evidence and skill lifecycle

2. Codebase Intake Service
   - accepts repo zip upload
   - unpacks into isolated workspace
   - creates codebase record

3. Repo Profiler
   - detects language
   - detects framework
   - detects package manager
   - infers install and test commands
   - infers source dirs, test dirs, and entrypoints

4. Discovery Engine
   - runs baseline tests
   - scans static signals
   - uses LLMs to generate adversarial probes
   - runs probes and candidate tests
   - captures failing scenarios
   - ranks the best failure candidate

5. Failure Case Store
   - saves reproducible failures
   - stores failing commands, inputs, outputs, and suspect files
   - supports replay mode

6. Repair Engine
   - builds diagnosis and patch requests
   - prefers skill-guided repair when a relevant skill exists
   - falls back to open-ended repair when no skill matches

7. Skill Library Service
   - loads skill assets from `skill_assets/`
   - indexes skills by structured bug signals and semantic descriptors
   - returns candidate matches for a failure case

8. Skill Synthesizer
   - creates a new skill after a validated repair with no adequate match
   - updates a matched skill when the match was directionally correct but insufficient
   - versions every skill change

9. Evaluator Engine
   - runs deterministic checks before and after repair
   - validates baseline tests, repro steps, and any materialized generated tests

10. Evidence Service
   - stores prompts, diffs, logs, repro steps, skill decisions, and verdicts

### LLM Roles
- probe generation
- candidate test generation
- failure triage and suspect-file ranking
- diagnosis
- patch generation
- skill creation
- skill update

### Deterministic Gates
- LLMs may propose probes, tests, and evaluators
- nothing can affect merge confidence unless it is materialized and rerun deterministically
- no repair skill can be promoted to reusable status unless the associated repair passes deterministic validation

## API Surface

### Existing Core
#### `POST /api/v1/runs`
Create a run.
Request fields should evolve to include:
- `mode`: `discover | inject | replay`
- `codebase_id`: optional for uploaded repos, required for `discover` and most `replay`
- `failure_case_id`: optional for `replay`
- `provider`: `openai`
- `model`: string
- `break_type`: optional and only relevant for `inject`
- `seed`: optional integer for deterministic inject or replay behavior

#### `GET /api/v1/runs`
List runs for the dashboard.

#### `GET /api/v1/runs/{run_id}`
Return run summary, current state, and evidence references.

#### `GET /api/v1/runs/{run_id}/events`
Server-sent events stream for timeline updates.

#### `POST /api/v1/runs/{run_id}/retry`
Retry the same run with a different model or provider configuration.

### V2 Additions
#### `POST /api/v1/codebases/upload`
- upload a zip
- create isolated workspace copy
- build and return a `RepoProfile`

#### `GET /api/v1/codebases/{id}`
- return codebase metadata and detected profile

#### `GET /api/v1/failure-cases/{id}`
- return exact repro details and stored failure evidence

#### `POST /api/v1/failure-cases/{id}/repair`
- repair a known failure case
- optionally force a specific skill or disable skill reuse for comparison

#### `GET /api/v1/skills`
- list learned repair skills

#### `GET /api/v1/skills/{id}`
- return skill metadata, revision history, and linked failure cases

## Data Model

### RepoProfile
- id
- source_type
- workspace_path
- language
- framework
- install_command
- test_command
- source_dirs
- test_dirs
- entrypoints
- risk_areas

### FailureCase
- id
- codebase_id
- failure_type
- title
- probe_input
- failing_command
- failing_output
- reproduction_steps
- suspect_files
- severity
- confidence
- deterministic_check_ids

### RepairSkill
- id
- slug
- title
- bug_family
- trigger_signals
- applicability_rules
- required_context
- investigation_flow
- repair_strategy
- verification_recipe
- exemplar_failure_case_ids
- version
- status
- created_from_failure_case_id
- last_updated_from_failure_case_id
- usage_count
- success_count

### SkillMatch
- skill_id
- failure_case_id
- match_reason
- confidence
- applied
- sufficient

### Run
- id
- created_at
- codebase_id
- mode
- failure_case_id
- provider
- model
- status
- verdict
- skill_match_id

### Evidence Packet
- run_id
- repo_profile_summary
- failure_case_summary
- failed_checks_before
- passed_checks_after
- root_cause_summary
- patch_summary
- skill_decision
- merge_confidence
- artifact_manifest

## Discovery Engine Responsibilities

- baseline test run
- static signal scan
- probe generation for:
  - invalid input
  - null and empty cases
  - contract mismatches
  - numeric edge cases
  - duplicate calls and retries
  - missing config assumptions
- candidate test materialization when useful
- capture of real failures
- ranking and minimization to one clean repro

## Skill Asset Design

### Why It Is Separate
- these are durable product assets, not ephemeral run logs
- they must be readable by the runtime like indexed knowledge assets
- they must not be mixed into repo-local Codex skills

### What A Skill Contains
- structured metadata for matching
- a focused investigation flow
- a repair recipe
- a verification recipe
- linked examples of successful past cases

### Skill Lifecycle
1. failure discovered
2. candidate skills matched
3. best skill chosen or no-match recorded
4. repair attempted
5. deterministic validation run
6. if validated:
   - create a new skill when unmatched
   - update the matched skill when insufficient
   - record successful reuse when sufficient

### Skill Update Rules
- never overwrite a skill without versioning
- keep prior revisions for replay and auditability
- store why the old flow was insufficient
- store which new signals or steps were added

## Execution Flow

### Discover
1. user uploads a repo zip
2. backend creates an isolated workspace
3. repo profiler builds a `RepoProfile`
4. baseline tests and entrypoint checks run
5. discovery engine generates and executes probes
6. one clean reproducible `FailureCase` is selected
7. skill library searches for matching repair skills
8. repair engine builds a skill-guided or open-ended repair request
9. patch service applies the returned patch
10. evaluator engine reruns baseline checks and repro steps
11. evidence service writes the final packet
12. skill synthesizer creates, updates, or records reuse of a repair skill
13. frontend shows failure, repair, learned skill decision, and verdict

### Inject
1. backend copies the fallback demo repo
2. seeded mutation is applied
3. evaluators fail
4. repair proceeds through the same skill-aware path
5. validated fix still participates in skill creation or update

### Replay
1. stored `FailureCase` is loaded
2. repro is rerun against a fresh workspace
3. current skill library is consulted
4. repair and validation run again
5. evidence compares current outcome to prior outcome

## Delivery Sequence

### Phase 0: Foundation
- keep the existing backend and frontend scaffold
- preserve V1 inject mode as a fallback
- keep provider adapters isolated

### Phase 1: External Codebase Intake
- add zip upload
- create isolated workspaces
- add `RepoProfile`
- detect install and test commands

### Phase 2: Discovery Mode
- add `discover` run mode
- baseline test detection
- static scan plus LLM probe generation
- capture reproducible `FailureCase`

### Phase 3: Learning Core
- add persistent `skill_assets/`
- implement skill matching
- implement skill creation after validated fixes
- implement skill versioning and updates

### Phase 4: Skill-Guided Repair
- route repair through matched skills first
- fall back to open-ended repair when needed
- compare skill-guided vs non-skill-guided outcomes

### Phase 5: Replay And UI Expansion
- add replay mode
- add repo profile, discovery, failure case, and skill library screens
- show skill creation, reuse, and update in the run timeline

### Phase 6: Separate Demo Repo And Polish
- build `adaptive-harness-demo-billing` outside this repo
- seed hidden latent failures
- use it as the primary V2 showcase

## Future-Proofing Rules

The system must be able to absorb future model jumps.
Design for that now by keeping these boundaries:
- provider adapters must be isolated
- evaluators must be deterministic and versioned
- failure cases must be replayable
- skill assets must be versioned and attributable
- prompts must be stored and attributable per run
- no UI language should imply the product is a chatbot

## Priority Rules

If there is a conflict between broadening the product and strengthening the evolving harness loop, prioritize:
1. reproducible discovery
2. deterministic validation
3. persistent skill learning
4. skill reuse and update
5. demo polish

Do not trade away replayability or evidence quality for generic agent behavior.

## Success Criteria

V2 is done when:
- a user uploads a repo zip
- the harness profiles the codebase
- the harness discovers a real failure without source mutation
- the harness captures a reproducible `FailureCase`
- OpenAI proposes a patch
- deterministic checks validate the fix
- the harness creates or updates a reusable repair skill in `skill_assets/`
- a later similar failure can be routed through that learned skill
- the UI shows:
  - codebase profile
  - discovered failure
  - repair
  - learned skill decision
  - final verdict

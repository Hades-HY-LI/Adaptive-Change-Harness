# V2 Implementation Plan

## Purpose

This plan translates the V2 product direction into a staged implementation path for the current repository.
It assumes the updated thesis:
- primary mode is `discover`
- `inject` stays as a fallback demo mode
- `replay` reruns saved failures
- the harness must learn by creating, reusing, and updating product repair skills in `skill_assets/`

This document is a review gate.
Do not begin implementation until this plan is reviewed and approved.

## Goals

V2 is successful when the harness can:
1. ingest a real Python service repo from a zip upload
2. profile the repo and infer how to run it
3. discover a real failure without mutating source first
4. capture a reproducible `FailureCase`
5. repair the failure with LLM support
6. validate the fix with deterministic checks
7. create or update a reusable repair skill in `skill_assets/`
8. reuse that skill on a similar future failure

## Non-Goals

- arbitrary language support
- enterprise auth and multi-tenant permissions
- broad architecture review
- turning the product into a generic agent platform

## Current Baseline

The repo is still V1-shaped:
- backend run creation is centered on `inject`
- persistence only stores runs and run events
- workspaces are copied from `demo-repo/`
- frontend only supports injected runs

Relevant current files:
- [apps/api/app/models/schemas.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/models/schemas.py)
- [apps/api/app/storage/repository.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/storage/repository.py)
- [apps/api/app/services/orchestrator.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/services/orchestrator.py)
- [apps/api/app/services/workspace.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/services/workspace.py)
- [apps/api/app/api/routes/runs.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/api/routes/runs.py)
- [apps/web/src/lib/types.ts](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/lib/types.ts)
- [apps/web/src/lib/api.ts](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/lib/api.ts)
- [apps/web/src/features/runs/RunCreateForm.tsx](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/features/runs/RunCreateForm.tsx)
- [apps/web/src/app/App.tsx](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/app/App.tsx)

## Guiding Constraints

- Keep provider-specific logic inside `providers/`
- Keep deterministic validation as the final gate
- Keep all discovery and repair execution inside isolated workspaces
- Keep generated product skills in `skill_assets/`, not `skills/`
- Preserve `inject` mode until `discover` is stable

## Discovery Vs Validation

This distinction is core to V2.

Discovery should be adaptive:
- LLMs may propose probes
- LLMs may suggest candidate tests
- LLMs may suggest likely failure families, suspect files, and repair strategies

Validation must be deterministic:
- a saved repro command or input should produce the same result given the same workspace
- baseline checks must be rerunnable
- generated tests only count after they are materialized and rerun as concrete artifacts
- run verdicts and skill promotion decisions must depend on reproducible evidence, not on model judgment alone

Working rule:
1. LLMs explore what to try.
2. The harness materializes exact commands, requests, or tests.
3. The harness reruns those artifacts deterministically.
4. Only then can the result affect verdicts, stored failure cases, or learned skills.

## Delivery Order

### Phase 1: Data Model And Storage Foundation

Objective:
- extend the persistence layer so V2 concepts exist before orchestration changes begin

Backend changes:
- expand run modes from `inject | verify` to `discover | inject | replay`
- add a first-class V2 verdict for `no_reproducible_failure_found`
- add `RepoProfile`, `FailureCase`, `RepairSkill`, and `SkillMatch` schemas
- extend SQLite schema to store:
  - codebases
  - failure cases
  - repair skills
  - skill revisions
  - skill matches
  - run references to codebase and failure case

Files to change:
- [apps/api/app/models/schemas.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/models/schemas.py)
- [apps/api/app/storage/repository.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/storage/repository.py)

Likely new files:
- `apps/api/app/storage/skill_repository.py`
- `apps/api/app/storage/codebase_repository.py`

Acceptance criteria:
- API models can represent V2 runs and skill metadata
- run verdicts can explicitly represent the case where discovery found no reproducible failure
- repository layer can create and retrieve codebases, failure cases, and skills
- existing V1 inject flow still works

### Phase 2: External Demo Repo

Objective:
- create the external V2 showcase target before backend discovery work starts

Work outside this repo:
- create `adaptive-harness-demo-billing`
- use Python + FastAPI + pytest
- include 20 to 40 tests
- seed a few latent failures that discovery can realistically find

Acceptance criteria:
- the harness target repo exists outside this repo
- it is zip-ingestable
- it contains at least one believable latent failure suitable for discovery work

### Phase 3: Codebase Intake And Workspace Isolation

Objective:
- support zip upload and create codebase-specific isolated workspaces

Backend changes:
- add upload endpoint for codebases
- unpack uploaded zips into managed workspace roots
- create a persistent codebase record
- separate uploaded codebase storage from per-run workspace copies

Files to change:
- [apps/api/app/api/router.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/api/router.py)
- [apps/api/app/services/workspace.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/services/workspace.py)

Likely new files:
- `apps/api/app/api/routes/codebases.py`
- `apps/api/app/services/codebase_intake.py`

Acceptance criteria:
- user can upload a zip through the API
- uploaded codebase is unpacked once and referenced by `codebase_id`
- each run still executes in a fresh isolated workspace copy

### Phase 4: Repo Profiling

Objective:
- infer enough about the repo to support baseline validation and discovery

Backend changes:
- detect:
  - language
  - framework
  - package manager
  - install command
  - test command
  - source dirs
  - test dirs
  - entrypoints
  - basic risk areas
- store the resulting `RepoProfile`

Likely new files:
- `apps/api/app/services/repo_profiler.py`

Files to change:
- `apps/api/app/services/codebase_intake.py`
- [apps/api/app/models/schemas.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/models/schemas.py)
- [apps/api/app/storage/repository.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/storage/repository.py)

Acceptance criteria:
- a newly uploaded repo returns a `RepoProfile`
- baseline install and test commands are inferred or explicitly marked unknown
- profiling emits a `codebase_profiled` event during runs

### Phase 5: Discovery Engine

Objective:
- find a real latent failure without mutating source first

Backend changes:
- add a `discover` branch in the orchestrator
- run baseline tests and entrypoint checks
- use LLMs to generate adversarial probes
- execute probes safely inside the workspace
- capture and rank failing scenarios
- minimize one clean repro into a stored `FailureCase`

Files to change:
- [apps/api/app/services/orchestrator.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/services/orchestrator.py)
- [apps/api/app/api/routes/runs.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/api/routes/runs.py)

Likely new files:
- `apps/api/app/services/discovery_engine.py`
- `apps/api/app/services/failure_cases.py`
- `apps/api/app/services/probe_runner.py`

Acceptance criteria:
- `POST /api/v1/runs` can start a `discover` run against a codebase
- a run produces either a saved `FailureCase` or a defensible “no reproducible failure found” result
- discovery events stream over SSE

### Phase 6: Skill Library Foundation

Objective:
- make repair-skill retrieval and storage real before repair starts depending on it

Backend changes:
- define on-disk layout for `skill_assets/`
- create skill manifests and revision records
- add `GET /api/v1/skills` in the first V2 slice
- implement skill lookup using:
  - failure type
  - trigger signals
  - suspect files
  - semantic descriptors
- record why a skill matched

Files to change:
- [skill_assets/README.md](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/skill_assets/README.md)
- [apps/api/app/storage/repository.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/storage/repository.py)

Likely new files:
- `apps/api/app/services/skill_library.py`
- `apps/api/app/services/skill_matcher.py`
- `apps/api/app/services/skill_assets.py`

Acceptance criteria:
- the runtime can list available repair skills
- a `FailureCase` can produce zero or more candidate skill matches
- skill matching is explainable in stored evidence

### Phase 7: Skill-Guided Repair Loop

Objective:
- route diagnosis and patch generation through skills when possible

Backend changes:
- update repair prompting to include:
  - failure repro
  - failing output
  - suspect files
  - matched skill guidance when available
- fall back to open-ended repair when no skill matches
- rerun baseline checks plus the exact repro after patching
- store skill decision in the evidence packet

Files to change:
- [apps/api/app/services/orchestrator.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/services/orchestrator.py)
- [apps/api/app/services/prompts.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/services/prompts.py)
- [apps/api/app/services/patcher.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/services/patcher.py)
- [apps/api/app/models/schemas.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/models/schemas.py)

Likely new files:
- `apps/api/app/services/repair_engine.py`

Acceptance criteria:
- successful repairs can be traced to either skill-guided or open-ended flow
- verdicts still depend only on deterministic checks
- evidence shows whether a skill was matched and whether it was sufficient

### Phase 8: Skill Synthesis And Update

Objective:
- allow the product to learn after validated repairs

Backend changes:
- after a validated repair:
  - create a new skill if no adequate match existed
  - update the matched skill if it helped but was incomplete
  - record successful reuse if the matched skill was sufficient
- version all skill updates
- link skill revisions back to the triggering `FailureCase`

Likely new files:
- `apps/api/app/services/skill_synthesizer.py`

Files to change:
- `apps/api/app/services/skill_library.py`
- [apps/api/app/services/orchestrator.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/services/orchestrator.py)
- [apps/api/app/models/schemas.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/models/schemas.py)

Acceptance criteria:
- validated repairs create or update assets in `skill_assets/`
- the system preserves immutable revision history
- later runs can see and use newly learned skills

### Phase 9: Replay Mode

Objective:
- make the learning loop testable and demonstrable

Backend changes:
- add `replay` mode to load an existing `FailureCase`
- recreate a clean workspace
- rerun the same repro and current repair flow
- compare current result against the original saved case

Files to change:
- [apps/api/app/services/orchestrator.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/services/orchestrator.py)
- [apps/api/app/api/routes/runs.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/api/routes/runs.py)
- [apps/api/app/models/schemas.py](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/api/app/models/schemas.py)

Acceptance criteria:
- a stored failure case can be rerun from the API
- replay uses the current skill library
- replay evidence makes before/after comparison clear

### Phase 10: Frontend V2 Console

Objective:
- replace the V1 inject-only console with the V2 run story

Frontend changes:
- extend types for:
  - `RepoProfile`
  - `FailureCase`
  - `RepairSkill`
  - V2 run shapes
- add codebase upload and mode selection
- show repo profile, discovery progress, failure case, repair, and skill decision
- add skill library view or panel

Files to change:
- [apps/web/src/lib/types.ts](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/lib/types.ts)
- [apps/web/src/lib/api.ts](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/lib/api.ts)
- [apps/web/src/app/App.tsx](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/app/App.tsx)
- [apps/web/src/features/runs/RunCreateForm.tsx](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/features/runs/RunCreateForm.tsx)
- [apps/web/src/features/runs/RunDetail.tsx](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/features/runs/RunDetail.tsx)
- [apps/web/src/features/runs/RunList.tsx](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/apps/web/src/features/runs/RunList.tsx)

Likely new files:
- `apps/web/src/features/codebases/CodebaseUpload.tsx`
- `apps/web/src/features/codebases/RepoProfilePanel.tsx`
- `apps/web/src/features/discovery/DiscoveryConsole.tsx`
- `apps/web/src/features/failures/FailureCasePanel.tsx`
- `apps/web/src/features/skills/SkillLibraryPanel.tsx`

Acceptance criteria:
- user can upload a repo and start a `discover` run from the UI
- the UI shows repo profile, active discovery, captured failure, repair result, and skill action
- `inject` mode remains available as a fallback

## Testing Plan

### Backend
- unit test schema changes and repository migrations
- unit test repo profiling logic
- unit test discovery ranking and failure-case normalization
- unit test skill matching and skill revision behavior
- integration test:
  - inject flow still works
  - discover flow finds and stores a failure case
  - repair flow validates correctly
  - validated fix creates or updates a skill
  - replay can reuse that skill

Likely test files:
- `apps/api/tests/test_repository_v2.py`
- `apps/api/tests/test_repo_profiler.py`
- `apps/api/tests/test_discovery_engine.py`
- `apps/api/tests/test_skill_library.py`
- `apps/api/tests/test_orchestrator_v2.py`

### Frontend
- component tests for new V2 panels
- end-to-end happy path once the UI stabilizes

## Sequencing Recommendation

Recommended implementation order:
1. Phase 1: data model and storage
2. Phase 2: external demo repo
3. Phase 3: codebase intake
4. Phase 4: repo profiling
5. Phase 5: discovery engine
6. Phase 6: skill library foundation
7. Phase 7: skill-guided repair
8. Phase 8: skill synthesis and update
9. Phase 9: replay mode
10. Phase 10: frontend V2 console

Reason:
- discovery cannot be credible without intake and profiling
- the demo repo should exist before discovery so probing is built against a concrete target
- skill learning should not be bolted on after repair; it needs storage and matching primitives first
- frontend work should follow stable backend contracts

## Risks To Watch Early

- upload and workspace isolation may become messy if codebase storage and run workspaces are not separated
- repo profiling will be brittle if command detection is too clever too early
- LLM-generated probes can create noise if failure ranking and minimization are weak
- generated skills will rot if they are stored as vague prose instead of structured assets
- replay value collapses if failure cases are not normalized and attributable

## Review Decisions

Approved decisions:
1. Keep skill library foundation and skill-guided repair as separate phases.
2. Include `GET /api/v1/skills` in the first V2 slice.
3. Make `no_reproducible_failure_found` a first-class run verdict in V2.
4. Build the external demo repo before backend discovery work starts.

## Review Gate

Implementation should not start until this plan is reviewed and approved.

# Adaptive Change Harness

Adaptive Change Harness is a verification and repair system for code changes and external codebases. It is built to discover real failures, reproduce them deterministically, repair them with model assistance, validate the result with hard gates, and learn reusable repair skills from validated fixes.

This is not a generic agent shell. The durable product value is:

- codebase intake and profiling
- reproducible failure-case capture
- deterministic validation and evidence
- patch orchestration
- a self-evolving repair-skill library

## Why It Gets Stronger Over Time

The product is designed to compound.

When a repair succeeds, the harness does not just return a patch. It also turns the validated result into a structured repair skill:

- `created` when no prior skill covers the failure
- `reused` when an existing skill already matches well
- `updated` when a matched skill was useful but needed refinement

That means each successful run can improve future runs. The harness gets stronger because it accumulates grounded repair knowledge tied to real failure cases and deterministic evidence, not because it stores generic chat transcripts.

## Product Loop

The main V2 loop is:

1. Upload a real Python service repository zip.
2. Profile the codebase and infer how to run it.
3. Run baseline deterministic checks.
4. Execute adaptive discovery probes.
5. Capture a reproducible `FailureCase`.
6. Replay the saved repro as the deterministic repair gate.
7. Ask the configured model provider for a grounded repair.
8. Apply the patch in an isolated workspace.
9. Rerun the saved repro plus baseline tests.
10. Record evidence and create, reuse, or update a repair skill.

## Repository Layout

```text
apps/
  api/    FastAPI backend
  web/    React + Vite frontend
artifacts/      local runtime outputs
demo-repo/      injected fallback demo target
docs/           plans and conventions
skill_assets/   product-generated repair skills
skills/         repo-local Codex/operator skills
```

## Running Locally

### Backend

From `apps/api`:

```bash
PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

The backend reads env vars from:

- `.env` at repo root, if present
- `apps/api/.env`

Important backend env vars:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `CORS_ORIGIN`
- `ARTIFACT_ROOT`
- `DATABASE_PATH`
- `SKILL_ASSETS_ROOT`
- `REQUEST_TIMEOUT_SECONDS`

### Frontend

From `apps/web`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8002 npm run dev -- --host localhost --port 5173
```

Open the app in the browser at the chosen Vite origin, for example:

```text
http://localhost:5173
```

Make sure `CORS_ORIGIN` on the backend matches the exact frontend origin.

## Using The Product

### Discover

Use `Discover` mode to test a real external repository.

1. Zip the target repository.
2. Upload it in the UI.
3. Start a discover run.
4. Wait for:
   - repo profile
   - baseline results
   - probe execution
   - a captured failure case or `no_reproducible_failure_found`

### Repair

If discovery captures a failure case:

1. Open the saved failure case panel.
2. Click `Repair this failure`.
3. The harness will:
   - replay the exact saved repro
   - call the configured provider for a repair
   - apply the patch
   - rerun the saved repro
   - rerun baseline tests

### Validate

A repair is only considered successful when deterministic gates pass.

Strong success criteria are:

- run `status = completed`
- run `verdict = safe`
- `reproduced_before_repair = true`
- `reproduced_after_repair = false`
- `saved_repro` passes after repair
- baseline tests pass after repair

## Evidence To Look For

The run console and API responses expose the main proof points:

- `diagnosis_ready`
- `patch_applied`
- `verdict_ready`
- replay comparison before versus after
- baseline evaluator output
- skill decision: `created`, `updated`, or `reused`

The final judgment should be based on deterministic validation, not just model confidence text.

## Repair Skills And Where They Live

The product-generated skill library is stored under `SKILL_ASSETS_ROOT`.

On disk, the structure is:

```text
skill_assets/
  manifests/
  skills/
  revisions/
  indexes/
```

You can inspect learned skills in three ways:

1. In the frontend skill panel.
2. Through the API:
   - `GET /api/v1/skills`
   - `GET /api/v1/skills/{id}`
3. On the backend filesystem at `SKILL_ASSETS_ROOT`.

### Local

By default, local runs write to:

```text
<repo>/skill_assets
```

### Deployed

Deployed runs write to the path configured by `SKILL_ASSETS_ROOT`.

Examples:

- Render demo setup with ephemeral storage:
  - `/tmp/adaptive-harness/skill_assets`
- Render production setup with persistent disk:
  - `/var/data/skill_assets`

If you want learned skills to survive restarts and redeploys, use a persistent disk and point `SKILL_ASSETS_ROOT` there.

## How Skills Are Created Automatically

Skills are created automatically after a repair passes deterministic validation.

That means:

- no manual admin step is required
- a successful replay repair can emit `skill_created`
- a later similar repair can emit `skill_reused`
- a partial match that needed refinement can emit `skill_updated`

If you want to seed a deployed environment with useful initial skills, the clean way is to run a few known high-value failure cases through the full replay repair flow. The product will learn from those runs and populate `SKILL_ASSETS_ROOT` automatically.

## Deploying

### Backend on Render

Recommended backend settings:

- Root Directory: `apps/api`
- Build Command:

```bash
pip install ".[dev]"
```

- Start Command:

```bash
PYTHONPATH=. python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- Health Check Path:

```text
/api/v1/health
```

Recommended Render env vars:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5
REQUEST_TIMEOUT_SECONDS=45
ARTIFACT_ROOT=/tmp/adaptive-harness/artifacts
DATABASE_PATH=/tmp/adaptive-harness/artifacts/harness.sqlite3
SKILL_ASSETS_ROOT=/tmp/adaptive-harness/skill_assets
DEMO_REPO_ROOT=/opt/render/project/src/demo-repo
CORS_ORIGIN=https://YOUR_VERCEL_APP_URL
```

For durable skill retention, move the artifact and skill paths onto a mounted persistent disk.

### Frontend on Vercel

Recommended frontend settings:

- Root Directory: `apps/web`
- Build Command:

```bash
npm run build
```

- Output Directory:

```text
dist
```

Required frontend env var:

```env
VITE_API_BASE_URL=https://YOUR_RENDER_BACKEND_URL
```

## Demo Usage

A strong demo sequence is:

1. Show a real external repo with a clean baseline.
2. Upload it into `Discover`.
3. Show a latent failure captured by the harness.
4. Open the saved repro and suspect context.
5. Trigger repair.
6. Show the replay run finish `safe`.
7. Show that the failure no longer reproduces.
8. Show baseline tests passing.
9. Show the learned repair skill appearing in the skill library.

## Current Scope

The current V2 slice is optimized for:

- Python service repositories
- FastAPI or similar layouts
- deterministic repro-based validation
- OpenAI-backed repair generation

It is not intended to be:

- a generic multi-language agent framework
- a broad architecture-review assistant
- a chat-first UI

## Key Principle

The harness should improve as stronger models arrive, not be replaced by them.

Models are workers inside the system. The durable product is the loop around them:

- discover
- reproduce
- repair
- validate
- learn

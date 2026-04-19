# Runtime Flow

This document explains what happens after a user uploads a repository zip, where the OpenAI API is used, and what role it plays in the product.

## High-Level Loop

The product loop is:

1. ingest a real repo
2. profile it
3. run deterministic baseline checks
4. discover a reproducible failure
5. replay the saved failure
6. ask OpenAI for a grounded repair
7. apply the patch
8. rerun deterministic validation
9. create, reuse, or update a repair skill

## Step-By-Step After Zip Upload

### 1. Upload And Store The Codebase

The backend accepts the uploaded zip and creates a `Codebase` record.

What happens:

- the uploaded zip is stored
- the archive is unpacked once
- a persistent `codebase_id` is created

OpenAI usage:

- none

### 2. Repo Profiling

The backend profiles the uploaded repo to infer how to operate on it.

What happens:

- detect language
- detect framework
- infer package manager
- infer install and test commands
- infer source dirs, test dirs, entrypoints, and risk areas

OpenAI usage:

- none in the current V2 implementation slice

### 3. Discover Run Starts

The system creates a fresh isolated workspace for the discover run.

What happens:

- the stored codebase is copied into a per-run workspace
- the run begins emitting events to the UI

OpenAI usage:

- none

### 4. Baseline Deterministic Validation

The harness runs deterministic baseline checks first.

What happens:

- run the inferred baseline test command
- establish whether the repo is green before adaptive probing

OpenAI usage:

- none

### 5. Discovery Probes Execute

The harness executes probes to find a latent, reproducible failure.

What happens:

- run candidate probes inside the isolated workspace
- evaluate probe output
- select a reproducible failure when one is found

OpenAI usage:

- the product thesis allows model-assisted discovery
- the current implementation uses product-defined deterministic probes rather than live OpenAI-generated probes

### 6. Failure Case Capture

The harness saves one clean `FailureCase`.

What happens:

- save the exact failing command
- save the failing output
- save suspect files
- save deterministic check ids
- save repro steps

OpenAI usage:

- none

### 7. Replay Repair Run Starts

When the user clicks `Repair this failure`, a replay run begins from the saved failure case.

What happens:

- create a fresh isolated workspace
- restore any saved probe artifacts needed for replay

OpenAI usage:

- none yet

### 8. Saved Repro Replays First

The exact saved repro is rerun before repair.

What happens:

- the system re-executes the saved failing command
- this proves whether the bug still reproduces before patching

OpenAI usage:

- none

### 9. Grounded Repair Prompt Is Built

The backend prepares a repair prompt from real evidence.

What goes into the prompt:

- failure title and type
- exact failing command
- failing output
- suspect files
- repo profile
- matched skill guidance, if available
- relevant code context

OpenAI usage:

- not yet
- this is the preparation step for the model call

### 10. OpenAI Generates The Repair

This is the primary OpenAI step in the current V2 loop.

What happens:

- the backend calls the configured OpenAI model through the provider adapter
- the model returns structured repair JSON

Expected response shape:

- `root_cause_summary`
- `patch_summary`
- `merge_confidence`
- `patches[]`

What OpenAI is doing here:

- diagnosing the likely root cause from grounded evidence
- proposing a minimal patch
- summarizing the intended repair

### 11. Patch Application

The backend applies the returned patch inside the isolated workspace.

What happens:

- patch operations are applied to target files
- changed files are recorded in run evidence

OpenAI usage:

- none

### 12. Deterministic Validation After Repair

The harness reruns hard gates after patching.

What happens:

- rerun the saved repro
- rerun the baseline tests
- compare before versus after

OpenAI usage:

- none

### 13. Verdict

The harness decides whether the repair is safe.

What happens:

- if the saved repro no longer fails and baseline tests pass, verdict is `safe`
- if deterministic validation still fails, verdict is `unsafe`
- if the run crashes before completion, the run fails and may surface `needs_review`

OpenAI usage:

- none

Important product rule:

- the final decision comes from deterministic validation, not from model confidence text alone

### 14. Skill Learning

If the repair passes deterministic validation, the harness updates the product skill library.

What happens:

- create a new repair skill when no prior skill fits
- reuse an existing skill when a match is already sufficient
- update an existing skill when the match was useful but incomplete

Skill assets are written under `SKILL_ASSETS_ROOT`.

OpenAI usage:

- none directly in the current implementation
- the learned skill is derived from the validated repair result

### 15. Evidence Visualization

The UI shows the full run story.

What the operator sees:

- discovery console
- saved failure case
- before/after replay comparison
- patch summary
- deterministic evaluator output
- skill decision
- learned skill in the skill panel

## Where OpenAI Is Used

In the current implemented V2 backend, OpenAI is used primarily during repair generation.

That means:

- not for final verdicts
- not for deterministic validation
- not for baseline test execution
- not for final skill promotion decisions by itself

OpenAI is used to:

- infer root cause from grounded evidence
- propose a minimal patch
- summarize the repair

## What OpenAI Does Not Decide

OpenAI does not decide whether a repair is truly accepted.

The harness requires:

- failure reproduced before repair
- failure no longer reproduced after repair
- baseline deterministic checks passing after repair

Only then can the run be considered `safe` and only then can the system promote the result into a reusable repair skill.

## Why This Matters

This is what makes the product self-evolving without becoming a generic chatbot.

The product gets stronger through:

- saved reproducible failure cases
- grounded repair prompts
- deterministic before/after validation
- reusable repair skills written from validated fixes

Models are workers inside the loop. The loop itself is the product.

# Adaptive Change Harness

This repository is for a JetBrains x OpenAI hackathon project: an adaptive code-change verification harness that can break, diagnose, repair, and validate code changes before merge.

## Read First

Before making non-trivial changes, read these files in order:
1. [docs/executable-plan.md](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/docs/executable-plan.md)
2. [docs/conventions.md](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/docs/conventions.md)
3. [docs/operator-checklist.md](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/docs/operator-checklist.md) if the task touches deployment, secrets, accounts, or hosting.
4. [skills/project-skill-finder/SKILL.md](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/skills/project-skill-finder/SKILL.md) when the task is ambiguous or needs routing to the right repo docs and installed skills.

Always use the OpenAI developer documentation MCP server if you need to work with the OpenAI API, ChatGPT Apps SDK, Codex, or related docs without me having to explicitly ask.

## Product Thesis

The product is not a generic agent framework.
The product is a code-change harness whose durable value is:
- repo-specific evaluators and invariants
- reproducible failure cases
- repair orchestration
- evidence for safe or unsafe merge decisions

Models are replaceable workers inside the harness. Stronger models should improve the product, not obsolete it.

## Hackathon Scope

The project must stay visibly inside the required coding tracks.
Primary track mapping:
- Track 2: testing and debugging
- Track 1: patch generation and repair
- Track 3: optional merge-safety summary

Do not turn this into:
- a generic chatbot
- a broad agent platform
- a thin RAG wrapper
- a pure architecture-review assistant

## Canonical Definition Of Break

For V1, "break" means a change or perturbation that causes a verifiable violation.

MVP break classes:
- logic regression
- contract violation
- repo invariant or pattern violation

Non-blocking review classes:
- architecture smell
- refactor quality concerns
- maintainability concerns
- speculative system design issues

Do not promote advisory review findings into hard failures unless there is a deterministic evaluator behind them.

## Target Architecture

The implementation plan assumes:
- `apps/web`: React + TypeScript + Vite frontend
- `apps/api`: FastAPI backend
- `demo-repo/`: deterministic target codebase used in the demo
- `artifacts/`: generated diffs, logs, evidence packets, and run outputs
- `docs/`: product plan and conventions
- `skills/`: repo-local custom skills

Keep the backend responsible for:
- model provider adapters
- run orchestration
- evaluator execution
- patch generation and application
- artifact storage

Keep the frontend responsible for:
- run creation
- evidence visualization
- timeline streaming
- diff review
- merge-confidence presentation

## Build Order

Default sequence unless the user explicitly changes direction:
1. Scaffold the backend API and run model.
2. Create the deterministic demo repo and evaluator suite.
3. Implement the break, diagnose, repair, validate loop.
4. Add the frontend timeline, diff, and evidence views.
5. Add deployment and demo polish.

## Technical Guardrails

- Every run must be reproducible from stored input, selected provider, selected model, evaluator outputs, and produced patch.
- No patch should be marked safe without at least one deterministic evaluator passing after the patch.
- Keep provider integrations behind an adapter interface. Do not scatter provider-specific request shapes through the codebase.
- Favor contract-first APIs and typed payloads.
- Shell execution must be explicit, logged, time-bounded, and rooted in a known workspace.
- Start with SQLite for local persistence. Do not introduce Redis, Celery, or Postgres in V1 unless the user asks.
- Prefer simple in-process background jobs for the hackathon build.

## UI Guardrails

- No chat-first interface.
- The primary screen is a run console with evidence, status, diff, and evaluator output.
- Use the design system described in [docs/conventions.md](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/docs/conventions.md).
- Avoid generic purple-on-white SaaS styling.

## Skills To Use

If the matching skills are available in Codex, prefer them:
- `project-skill-finder`: route ambiguous repo tasks
- `openai-docs`: OpenAI and Codex documentation work
- `frontend-skill`: frontend implementation work
- `playwright`: browser testing and demo verification
- `security-best-practices`: shell execution, secret handling, and patch safety review
- `cli-creator`: CLI design for local harness commands
- `vercel-deploy`: frontend deployment
- `render-deploy`: backend deployment

## Definition Of Done For V1

A strong V1 demo must show:
1. a clean baseline run
2. an introduced or detected break
3. deterministic evaluator failure
4. OpenAI-powered diagnosis
5. OpenAI-generated repair
6. deterministic evaluator success
7. a concise safe-to-merge evidence summary

## Provider Policy For V1

- OpenAI is the only required live provider in V1.
- Anthropic support is optional and can be added later behind the same provider interface.
- Do not block scaffolding, startup, or deployment on an Anthropic API key.
- The API and UI should expose only configured providers.

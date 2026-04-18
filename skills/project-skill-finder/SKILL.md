---
name: project-skill-finder
description: Route work in this repository to the right project docs, architectural rules, and installed Codex skills. Use when a task is ambiguous, spans frontend and backend, touches the harness workflow, or needs the right skill and convention stack for this hackathon project.
---

# Project Skill Finder

Use this skill when the request is broad or it is unclear which repo docs and external skills should guide the work.

## Workflow

1. Read [docs/executable-plan.md](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/docs/executable-plan.md) for product scope, stack, APIs, and delivery order.
2. Read [docs/conventions.md](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/docs/conventions.md) for implementation guardrails.
3. Read [docs/operator-checklist.md](/Users/lihongye/Desktop/Developer/Jetbrains_Hackathon/docs/operator-checklist.md) if the task touches deployment, accounts, secrets, MCP setup, or demo operations.
4. Map the task to the right installed skills:
   - `openai-docs` for OpenAI and Codex docs
   - `frontend-skill` for web UI implementation
   - `playwright` for browser tests and demo validation
   - `security-best-practices` for shell execution safety, secrets, and patch review
   - `cli-creator` for CLI commands and local developer workflows
   - `vercel-deploy` for frontend deployment
   - `render-deploy` for backend deployment
5. Keep all work aligned with these repo truths:
   - the product is a code-change verification harness, not a generic agent platform
   - V1 break classes are logic regression, contract violation, and invariant violation
   - advisory design critiques are not blocking failures in V1
   - the primary demo loop is break, evaluate, repair, validate, and summarize

## Decision Rules

### If the task is frontend-heavy
Use the web implementation plan and design conventions first. The UI should prioritize timeline, evaluator state, diff, and merge confidence over chat.

### If the task is backend-heavy
Protect determinism, evaluator clarity, provider abstraction, and artifact capture before adding complexity.

### If the task is deployment-heavy
Keep the split simple:
- frontend on Vercel
- API on Render

### If the task is product-ambiguous
Prefer features that strengthen the harness thesis:
- clearer evaluators
- better evidence
- cleaner provider abstraction
- stronger replayability

Reject features that make the product look like a generic coding chatbot.

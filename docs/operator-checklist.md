# Operator Checklist

This file is the human checklist for accounts, hosting, secrets, and one-time setup outside the repo.

## Accounts You Need

### Required
- GitHub repository for the project
- OpenAI API account and API key
- Vercel account for the frontend
- Render account for the backend

### Optional
- Anthropic API account and API key
- custom domain for demo polish
- Sentry account for runtime error tracking after V1

## Secrets To Prepare

### Backend Secrets
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY` optional
- `DATABASE_URL` for SQLite or later Postgres migration
- `ARTIFACT_ROOT`
- `DEMO_REPO_ROOT`
- `CORS_ORIGIN`
- `DEFAULT_PROVIDER`
- `DEFAULT_MODEL`

### Frontend Secrets And Vars
- `VITE_API_BASE_URL`

## Hosting Plan

### Frontend
Deploy `apps/web` to Vercel.
Recommended settings:
- framework preset: Vite
- build command: project-specific once scaffolded
- output directory: project-specific once scaffolded
- env var: `VITE_API_BASE_URL`

### Backend
Deploy `apps/api` to Render as a web service.
Recommended settings:
- Python runtime
- health check path: `/api/v1/health`
- persistent disk only if local artifact retention is needed after deploy
- set all provider and app env vars in Render dashboard

## What You Should Do On Your Side

1. Create the GitHub repo and push this workspace.
2. Create Vercel and Render projects connected to the repo.
3. Generate OpenAI and Anthropic API keys.
4. Generate an Anthropic key only if and when you decide to enable that provider.
5. Add backend secrets in Render.
6. Add `VITE_API_BASE_URL` in Vercel after the Render API URL exists.
7. Decide whether you want a custom domain. If yes, point it to Vercel after the first deploy works.
8. Keep one seeded demo dataset and one fallback recorded run for live-demo risk reduction.

## Local Setup Checklist

1. Restart Codex to pick up newly installed skills.
2. If you use Codex CLI or IDE tooling, add the OpenAI docs MCP server:
   - `codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp`
3. Copy local env files once the scaffold exists.
4. Run the backend and frontend locally before touching deployment.

## Demo Operations Checklist

Before demo:
1. verify OpenAI and Anthropic keys still work
2. run one clean end-to-end repair flow locally
3. verify deployed frontend reaches deployed API
4. preload one deterministic run in case live repair latency spikes
5. have one script ready for a 90-second live narrative

During demo:
1. show baseline green state
2. trigger a break
3. show evaluator failure
4. show diagnosis and patch
5. end on green and merge confidence

# Project Guide

> **Project:** RAG Book Library AI Assistant. **Tech stack and stack policy:** [`.claude/rules/architecture.md`](.claude/rules/architecture.md) — FastAPI + uv backend (`apps/backend`), PostgreSQL + Qdrant (pgvector later), company embedding service, Agno + LiteLLM, SSE streaming, FastMCP (`apps/mcp/`), React web (`apps/web`), Docker. The boilerplate rules are **guidelines**: prefer them, and record deliberate deviations in `architecture.md`.

> **CRITICAL FIRST STEP — MANDATORY BEFORE ANY CODE:**
>
> 1. Run `ls apps/` to list all app directories.
> 2. Find and **read** every `AI_GUIDE.md` inside them (`apps/**/AI_GUIDE.md`) relevant to the current task.
> 3. From the `AI_GUIDE.md` Documentation Map, identify **all skills needed** for the task (architecture, slicing-ui, icon, state, etc.) and read them before writing a single line of code.
>
> ❌ **DO NOT write any file — no types, no service, no component, no store — until steps 1–3 above are complete.**
> Skipping `AI_GUIDE.md` causes wrong patterns (wrong icon library, wrong import style, wrong file placement). This has happened before and must not repeat.
>
> Stacks (web, backend, agents, mcp, mobile) are discovered dynamically — do NOT assume fixed folder names. Tasks for a specific stack are handled by their respective domain agent in [`agents/`](agents/).

## Skill Index

Read the index, pick **only** the skill relevant to the current task. Never load all skills blindly. All skills live under [`.claude/skills/`](.claude/skills/).

| Task                                                                                                                                                                                                                                                                                                                                       | Skill to load                                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| Buat desain HTML, build UI, buatkan UI, buat halaman, slice UI, design screen, design html web, design html mobile — **hanya jika tidak ada kata "react", "reactjs", atau target path `apps/`**; jika ada kata "html" eksplisit tetap gunakan skill ini meski ada kata "react"                                                             | [`html-ui-styling`](.claude/skills/html-ui-styling/SKILL.md)                          |
| Setup CSS assets, set design system, setup design system, init design system, init mockup folder                                                                                                                                                                                                                                           | [`design-system-setup`](.claude/skills/design-system-setup/SKILL.md)                  |
| Design tokens, generate CSS from palette, new theme folder, **buatkan design system**, bikin design system, buat design system untuk [project/brand/URL], create design system, build design system, design system untuk [project], buat token design, buat visual identity                                                                | [`.claude/skill/design-system-builder`](.claude/skill/design-system-builder/SKILL.md) |
| Setup existing design system config (no generation)                                                                                                                                                                                                                                                                                        | [`design-system`](.claude/skills/design-system/SKILL.md)                              |
| Figma, shadcn, apply tokens to app code (post-scaffold)                                                                                                                                                                                                                                                                                    | [`uiux`](.claude/skills/uiux/SKILL.md)                                                |
| Brief, dokumentasi sistem, Workforce Manifest                                                                                                                                                                                                                                                                                              | [`brief-builder`](.claude/skills/brief-builder/SKILL.md)                              |
| App spec, page inventory                                                                                                                                                                                                                                                                                                                   | [`spec-builder`](.claude/skills/spec-builder/SKILL.md)                                |
| Sprint planning, task breakdown per stack                                                                                                                                                                                                                                                                                                  | [`sprint-builder`](.claude/skills/sprint-builder/SKILL.md)                            |
| Any coding task (bug, feature, refactor)                                                                                                                                                                                                                                                                                                   | [`orchestra`](.claude/skills/orchestra/SKILL.md) first → domain reference             |
| Authoring or refining a skill                                                                                                                                                                                                                                                                                                              | [`skill-creator`](.claude/skills/skill-creator/SKILL.md)                              |
| Migrate ERP (Fusion) dashboard, parse `widgets_*.json` or `application_*.json`, scaffold pages from dashboard export, migrate ERP widgets to React, build BFF handlers from ERP queries, wire ECharts from styleConfig, GridStack grid from `{x,y,w,h}`, menu config from ERP sidebar, filter bar from `filter_configs`, widget drill-down | [`erp-dashboard-migrator`](.claude/skills/erp-dashboard-migrator/SKILL.md)            |

## Context Loading

**Auto-load:** ONLY load `rules/*.md` (root level). Do NOT auto-load nested rules (`rules/**/*.md`) unless specified.

| Task                   | Load                                   |
| ---------------------- | -------------------------------------- |
| Micro (typo, 1-line)   | nothing                                |
| Small (single file)    | relevant skill only                    |
| Medium (feature)       | agents → rules → skills for that stack |
| Large (cross-platform) | full orchestra, parallelize agents     |

## Global Workflow (skill-driven)

This project is built on top of Argus — an agent-driven app builder. The end-to-end workflow runs through the skills in [`.claude/skills/`](.claude/skills/), each invokable via a matching slash command under [`.claude/commands/`](.claude/commands/):

**Project lifecycle phases** (linear, run once per project):

| Phase                              | Slash command        | Skill                                                            | Output                                                                                                                                               |
| ---------------------------------- | -------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Brief**                       | `/brief-builder`     | [`brief-builder`](.claude/skills/brief-builder/SKILL.md)         | `brief/00_OVERVIEW.md` (with Workforce Manifest), `brief/NN_FEATURE.md`, optional `brief/AA_AGENT_<role>.md`                                         |
| **2. App spec**                    | `/spec-builder`      | [`spec-builder`](.claude/skills/spec-builder/SKILL.md)           | `sprint/00-app-spec.md` (single file — page inventory + widget per page + navigation map)                                                            |
| **3. Design tokens**               | `/design-system`     | [`design-system`](.claude/skills/design-system/SKILL.md)         | `design/{platform}/{theme}/` — `DESIGN.md`, `variable.css`, `tailwind.css`, `design-token.json`                                                      |
| **4. HTML mockups**                | `/html-ui-styling`   | [`html-ui-styling`](.claude/skills/html-ui-styling/SKILL.md)     | HTML pages under `mockup/{web,mobile}-html/` (uses [`design-system-setup`](.claude/skills/design-system-setup/SKILL.md) when CSS assets are missing) |
| **5. Supabase setup** _(not used in this project)_ | `/supabase-init` | [`supabase-init`](.claude/skills/supabase-init/SKILL.md) | Skipped — PostgreSQL runs via root `docker-compose.yml` |
| **6. Project scaffold** _(done — apps already scaffolded)_ | `/bootstrap-project` | [`bootstrap-project`](.claude/skills/bootstrap-project/SKILL.md) | `apps/backend` (be-fastapi) and `apps/web` exist; new Python projects use `uv init --app` |
| **7. Sprint plan**                 | `/sprint-builder`    | [`sprint-builder`](.claude/skills/sprint-builder/SKILL.md)       | `sprint/01-sprint-planning.md`, `sprint/{backlog,active,archive}/<sprint>/<stack>/<NN-task>.md`                                                      |
| **8. Agent build** | `/agent-builder` | [`agent-builder`](.claude/skills/agent-builder/SKILL.md) | RAG agent in `apps/backend/service/` (Agno + LiteLLM); optional standalone `apps/agents/<role>/` (MCPHub optional) |
| **9. MCP build** | `/mcp-builder` | [`mcp-builder`](.claude/skills/mcp-builder/SKILL.md) | `apps/mcp/<server>/` (uv, FastMCP; calls backend REST with `X-Internal-Token`; MCPHub optional) |

**Development cycle** (per-task, invoked repeatedly during sprint execution):

| Trigger                                             | Skill                                            | Role                                                                                                                                                                                                               |
| --------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| Any coding task starts (bug fix, feature, refactor) | [`orchestra`](.claude/skills/orchestra/SKILL.md) | Master task router. Classifies task size (Micro / Small / Medium / Large) and routes to the correct domain reference (`web`, `backend`, `mobile`, `agent`, `review`). Loaded BEFORE any other domain rules/skills. |
| Apply design system into scaffolded app             | `/switch-design-system`                          | —                                                                                                                                                                                                                  | Copies active tokens from `design/` into `apps/<web>/` (see `.claude/commands/switch-design-system.md`) |
| Figma / token resolution for app UI (post-scaffold) | —                                                | [`uiux`](.claude/skills/uiux/SKILL.md)                                                                                                                                                                             | Not a pipeline phase — load when implementing or updating UI inside `apps/`                             |

Skill authoring (orthogonal to both pipeline and dev cycle): trigger [`skill-creator`](.claude/skills/skill-creator/SKILL.md) directly when adding or refining a skill — no slash command, this is a meta workflow.

Sprint status: `backlog/` → `active/` → `archive/` (moved by sprint-builder).

## Decision Tree

| Situation                          | Action                                                                                                                                                                      |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Starting a new project             | `/brief-builder` → `/spec-builder` → `/design-system` → `/html-ui-styling` → `/bootstrap-project` (Supabase not used) → `/switch-design-system` → `/sprint-builder` |
| HTML mockup only (no app code yet) | `/html-ui-styling` (+ `/design-system-setup` if `mockup/*/css/` missing)                                                                                                    |
| New feature in existing project    | Check `sprint/active/` → if missing, promote from `sprint/backlog/` (`/sprint-builder`)                                                                                     |
| Starting any coding task           | Load [`orchestra`](.claude/skills/orchestra/SKILL.md) first → classify task size → route to domain reference                                                                |
| Need an agent                      | `/agent-builder` (in-backend Agno + LiteLLM agent by default; Workforce Manifest optional)                                                                                  |
| Need a bespoke MCP tool            | `/mcp-builder`                                                                                                                                                              |
| New file in an installed stack     | Read `.claude/rules/{platform}/{template}/orchestra.md` → determine path                                                                                                                          |

## Mindset

- **Backend is the single source of truth.** `apps/backend` (FastAPI) owns business rules, auth and all data access — PostgreSQL for domain data, Qdrant for vectors, MongoDB/Redis only for the legacy boilerplate modules.
- **The RAG agent lives in the backend service layer** (Agno + LiteLLM) and streams answers over SSE. Standalone agents in `apps/agents/<role>/` are optional; the be-python `agent_mgmt` plane is not used.
- **MCP servers are thin and read-only by default.** `apps/mcp/<name>/` (FastMCP) call the backend REST API with an `X-Internal-Token`; they never touch the databases directly and require inbound bearer-token auth.
- **Build incrementally and testably.** Each phase ends with something runnable and covered by tests (`uv run pytest`, `npm test`).

## Forbidden Rules

- **Never read or explore any files inside `mockup/`** unless the user explicitly asks. HTML previews in `mockup/` are output artifacts — treat them as opaque.
- **Never read `tailwind.css`, `variable.css`, or `variable_dark.css`** under `design/`. The canonical design reference is **`DESIGN.md`** in the active theme folder (`design/{platform}/{theme}/DESIGN.md`) — read [`design/design-system.md`](design/design-system.md) first to resolve platform + theme.

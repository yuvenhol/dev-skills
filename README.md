# dev-skills

A "field manual" for AI coding assistants. It captures the standards, workflows, and role constraints you'd otherwise repeat every time, so Codex, Claude Code, and friends can consult them on demand.

## Currently registered

| Skill | For whom | What it solves |
|-------|----------|----------------|
| `codex-orchestrator` | Codex | Complex task orchestration. Driven by `_workspace/` files, it dispatches work to architect / developer / reviewer / tester and wraps up serially or in parallel. |
| `cc-orchestrator` | Claude Code | Multi-agent collaboration. Forms a team with TeamCreate / SendMessage / TaskCreate and divides the work. |
| `python-dev-standards` | Python backend | FastAPI, Pydantic v2, SQLAlchemy async, configuration, testing, typing, exceptions, async I/O, unified error responses, Repository / Service layering — all in one place. |

## How to use

1. Hit a given domain → read that skill's `SKILL.md` first.
2. Need the details / templates / longer examples → then flip through `references/`.
3. Orchestration skills ship their own `agents/` for roles; plain standards skills don't need to force them in.

## Maintenance conventions

- `SKILL.md` only holds trigger boundaries, execution flow, and the reference index — keep it light.
- `references/` carries the full standards, long examples, templates, and decision details — keep it thick.
- Don't add a README / CHANGELOG / install guide to an individual skill unless it genuinely serves execution.
- When changing a standard, edit the reference first; only touch `SKILL.md` when the entry point, triggers, or resource index change.
- When adding or removing a skill, remember to come back and update the table above.

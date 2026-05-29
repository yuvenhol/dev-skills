---
name: python-dev-standards
description: Python backend development standards. Used for writing, reviewing, refactoring, or initializing Python backend projects, especially FastAPI, Pydantic v2, SQLAlchemy async, async I/O, configuration management, testing, unified error responses, Repository/Service layering, and toolchain configuration.
metadata:
  version: 1.0.0
---

# Python Development Standards

## Usage

- First determine the task type: new project initialization, existing project development, code review, refactoring, test supplementation, or documentation maintenance.
- Specific rules, code examples, and templates are all in `references/python-dev-standards.md`. That file is the sole canonical body of this skill.
- `SKILL.md` only keeps entry logic and section index to avoid duplicating detailed rules; if this file is inconsistent with the reference, the reference prevails.
- For existing projects, first read the local `pyproject.toml`, directory structure, runtime environment, CI, and existing tests, then decide which sections apply.

## Read Rules by Task

| Task | Read Sections |
|------|---------------|
| Initialize Python backend project | `1. Project Architecture`, `2. Toolchain Configuration Templates`, `3. Configuration Management`, `4. Testing Standards`, `14. Logging & Observability` |
| Develop FastAPI endpoints | `5. FastAPI Development`, `12. Unified Error Responses`, read `13. Database & Repository` when necessary |
| Design config or environment variables | `3. Configuration Management` |
| Write or adjust tests | `4. Testing Standards` |
| Clean up types, imports, naming | `6. Type Annotations`, `9. Import Standards`, `10. Naming Conventions` |
| Simplify complex conditionals or branching | `7. Control Flow & Code Complexity` |
| Review exception handling | `8. Exception Handling`, `12. Unified Error Responses` |
| Handle async, concurrency, or external calls | `11. Async I/O & Concurrency` |
| Design Repository, transactions, or migrations | `13. Database & Repository` |
| Configure logging or observability | `14. Logging & Observability` |

## Execution Guidelines

- When referencing standards, cite the specific section or file location; avoid saying just "according to the standard."
- When modifying existing projects, read local code and config first, then decide which standards apply; do not perform unrelated migrations just to match the template.
- When the standard conflicts with an explicit user requirement, point out the conflict and impact first, then proceed in the user-confirmed direction.
- When maintaining this skill, update `references/python-dev-standards.md` first; only modify `SKILL.md` when entry flows, trigger instructions, or section index changes.
- After completing code changes, prefer running the project's existing lint, type check, and related tests; for documentation or standard changes, do at least structural and keyword checks.

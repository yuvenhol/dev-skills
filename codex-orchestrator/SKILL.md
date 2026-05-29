---
name: codex-orchestrator
description: "General-purpose development task orchestrator. Breaks complex development tasks down into specialized agent roles and coordinates their collaboration. Use it when you need to 'form a team', 'decompose tasks', 'multi-agent collaboration', 'team-based development', 'parallel development', or 'team collaboration'. Follow-up tasks supported: 'modify the team', 'adjust the division of work', 're-run', 'update the plan', 're-run only a specific phase'. For simple tasks or single-file changes, just do them directly; only enable this when complexity genuinely requires multi-role collaboration."
metadata:
  version: 1.0.0
---

# Team Orchestrator — general-purpose development task orchestrator (Codex edition)

Break a complex development task down into specialized agent roles, pick a suitable architecture pattern, and coordinate completion through file-driven collaboration.

**Core principles:**
1. File-driven coordination — agents pass data through `_workspace/` files.
2. Sequential/parallel subtasks — dependencies are controlled by execution order.
3. Intermediate artifacts all go in `_workspace/` — naming convention `{phase}_{agent}_{artifact}.{ext}`.

## When to enable

- The user explicitly asks for "form a team", "multi-agent collaboration", "decompose the task", or "push forward in parallel".
- The task contains at least 2 subproblems that need different areas of expertise.
- The task needs intermediate design, review, or test artifacts explicitly preserved for later traceability.

Do NOT enable this orchestrator in the following cases — just do the work directly:
- Simple Q&A, small single-file changes, local bug fixes.
- Tasks that can be finished directly in the current session without a division of roles.
- You only need a single expert perspective rather than multi-role collaboration.

## Execution modes

Codex invokes agent roles via sequential or parallel subtasks. Agents don't communicate directly; instead they pass data through files.
If the current environment isn't suitable for true parallelism or multi-agent delegation, the current session plays each role serially in execution order, still using `_workspace/` to maintain intermediate artifacts and boundaries.

| Mode | Applicable scenario | Method |
|------|---------------------|--------|
| **Sequential** | Dependencies between stages | Invoke each role in order |
| **Parallel** | Independent tasks | Launch multiple roles at once |
| **Iterative** | Generate-verify | Loop until verification passes (at most 2 rounds) |

> See `references/pattern-selector.md` for the detailed mode-selection guide.

## Workflow

### Phase 0: Context confirmation

1. Check whether the current project's `_workspace/` directory exists.
2. Determine the execution mode:
   - `_workspace/` **does not exist** → initial run, proceed to Phase 1.
   - `_workspace/` **exists** + user requests a partial change → partial re-run (only re-run the relevant roles).
   - `_workspace/` **exists** + brand-new input → new run (back up the old `_workspace/` as `_workspace_{YYYYMMDD_HHMMSS}/`).
3. Identify the project's tech stack (check pyproject.toml / package.json / Cargo.toml / go.mod, etc.).

### Phase 1: Task analysis

1. Understand the user's task goals and constraints.
2. Determine the nature of the task (new feature / research / refactor / fix / docs / review).
3. Estimate the task size:
   - Small (1-2 concerns) → a single role finishes it directly.
   - Medium (3-5 concerns) → 2-3 roles.
   - Large (6+ concerns) → 3-5 roles.
4. Pick an architecture pattern per `references/pattern-selector.md`.
5. Pick the role combination per `references/agent-catalog.md`.
6. Decide whether explicit confirmation is needed:
   - When requirements are unclear, approaches diverge significantly, execution cost is high, or impact could be large → confirm with the user first.
   - When the user has already explicitly asked for team execution and the approach is clear with controllable risk → proceed directly to Phase 2.

### Phase 2: Execution plan

1. Draft the execution plan based on the Phase 1 analysis.
2. Write the plan into `_workspace/00_project_lead_plan.md`:
   - The list of roles and their responsibilities.
   - The execution order and dependencies.
   - The input and output file paths for each role.
3. Create the `_workspace/` directory.
4. If not using true multi-agent, the plan must also make clear "which roles the current session plays serially".

### Phase 3: Execution

Invoke each role sequentially or in parallel per the execution plan:

**Sequential task example (pipeline):**
```
1. Invoke architect → read requirements → output _workspace/01_architect_design.md
2. Invoke developer → read the design doc → output code + _workspace/02_developer_changelog.md
3. Invoke reviewer  → read design + changelog + code → output _workspace/03_reviewer_report.md
4. Invoke developer → read the review report → revise the code → update the changelog
5. Invoke tester    → read design + changelog + code → output _workspace/04_tester_report.md
```

**Parallel task example (fan-out/fan-in):**
```
1. Invoke researcher-A + researcher-B in parallel
   → each outputs _workspace/00_researcher_{topic}_findings.md
2. Aggregate all findings files → produce an integrated report
```

If the current environment isn't suitable for true parallelism:
```
1. researcher-A completes first and writes its file
2. researcher-B independently completes based on the same input and writes its file
3. Finally aggregate everything together
```

**Iterative task example (generate-verify):**
```
1. Invoke developer → output code
2. Invoke reviewer  → review → PASS? done : FIX?
3. Invoke developer → revise → back to step 2 (at most 2 rounds)
```

When each role executes:
- Read the input files specified in the plan.
- Execute the task.
- Write the artifact to `_workspace/{phase}_{agent}_{artifact}.{ext}`.
- If a single session plays multiple roles serially, you must explicitly switch perspective and use the previous role's artifact as the next role's input, avoiding "skipping steps" in your head.

### Phase 4: Integration and verification

1. Read every role's artifacts.
2. Check consistency:
   - Do both sides of an interface definition match?
   - Are there contradictions between artifacts?
3. Produce the final artifact.
4. Brief quality verification.

### Phase 5: Reporting

1. Report completion status and the location of key artifacts to the user.
2. Keep `_workspace/` for auditing and follow-up tasks.

## Common execution templates

### Feature development
```
architect → developer → reviewer → developer(revise) → tester
Pattern: sequential + iterative (review-revise)
```

### Technical research
```
researcher-A | researcher-B | researcher-C (parallel) → aggregate
Pattern: parallel → aggregate
```

### Code review
```
reviewer-security | reviewer-performance | reviewer-architecture (parallel) → aggregated report
Pattern: parallel → aggregate
```

### Large-scale refactoring
```
project-lead(plan) → developer-1 | developer-2 (parallel) → verify batch by batch
Pattern: sequential + parallel + iterative
```

### Full-stack development
```
architect → developer-frontend | developer-backend (parallel) → tester
Pattern: sequential + parallel + sequential
```

### Documentation improvement
```
tech-writer + researcher (sequential or parallel)
Pattern: parallel → sequential integration
```

## Error handling

| Situation | Strategy |
|-----------|----------|
| A role's artifact is missing | Check the blockers file, determine the cause, then re-invoke |
| Data conflict between artifacts | Annotate the sources side by side; don't delete either one |
| A role fails to execute | Retry once; if it still fails, skip it and annotate during integration |
| Timeout | Use the partial results already collected; mark unfinished items in the report |
| Critical blocker | Write it into the blockers file and notify the user to confirm |

## Data-passing conventions

All inter-agent data passing is done through files:

| File | Writer | Reader |
|------|--------|--------|
| `_workspace/00_project_lead_plan.md` | project-lead | all roles |
| `_workspace/00_researcher_{topic}_findings.md` | researcher | architect |
| `_workspace/01_architect_design.md` | architect | developer, reviewer, tester |
| `_workspace/02_developer_changelog.md` | developer | reviewer, tester |
| `_workspace/03_reviewer_report.md` | reviewer | developer |
| `_workspace/04_tester_report.md` | tester | developer |
| `_workspace/05_techwriter_docs.md` | tech-writer | reviewer |

## Conflict-resolution protocol

1. Data conflict → don't delete either side; annotate the sources and list them side by side.
2. Design disagreement → the architect has the final say, but must explain the reasoning.
3. Implementation diverges from design → annotate the difference in the changelog, and the architect makes the call.

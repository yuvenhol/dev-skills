---
name: cc-orchestrator
description: "General-purpose development task orchestrator. Breaks complex development tasks down into specialized agent roles and coordinates their collaboration. Use it when you need to 'form a team', 'decompose tasks', 'multi-agent collaboration', 'team-based development', 'parallel development', or 'team collaboration'. Follow-up tasks supported: 'modify the team', 'adjust the division of work', 're-run', 'update the plan', 're-run only a specific phase'. For simple tasks or single-file changes, just do them directly; only enable this when complexity genuinely requires multi-role collaboration."
metadata:
  version: 1.0.0
---

# Team Orchestrator — general-purpose development task orchestrator

Break a complex development task down into specialized agent roles, pick a suitable architecture pattern, and coordinate a team of agents to complete the task together.

**Core principles:**
1. An agent team is the default execution mode — prefer TeamCreate whenever there are 2 or more members.
2. Role definitions are separate from orchestration — agents are defined in `agents/`, the orchestration logic lives in this skill.
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

| Mode | Applicable scenario | Tools |
|------|---------------------|-------|
| **Agent team** (default) | 2+ agents need to collaborate and cross-check | TeamCreate + SendMessage + TaskCreate |
| **Sub-agent** | A single task, only the result needs to be returned | Agent tool + run_in_background |
| **Hybrid** | Phases have different characteristics | Switch modes per phase |

> See `references/pattern-selector.md` for the detailed mode-selection guide.

## Workflow

### Phase 0: Context confirmation

1. Check whether the current project's `_workspace/` directory exists.
2. Determine the execution mode:
   - `_workspace/` **does not exist** → initial run, proceed to Phase 1.
   - `_workspace/` **exists** + user requests a partial change → partial re-run (only re-run the relevant agents).
   - `_workspace/` **exists** + brand-new input → new run (back up the old `_workspace/` as `_workspace_{YYYYMMDD_HHMMSS}/`).
3. Identify the project's tech stack (check pyproject.toml / package.json / Cargo.toml / go.mod, etc.).

### Phase 1: Task analysis

1. Understand the user's task goals and constraints.
2. Determine the nature of the task (new feature / research / refactor / fix / docs / review).
3. Estimate the task size:
   - Small (1-2 concerns) → no team needed, sub-agent or do it directly.
   - Medium (3-5 concerns) → 2-3 person team.
   - Large (6+ concerns) → 3-5 person team.
4. Pick an architecture pattern per `references/pattern-selector.md`.
5. Pick the agent role combination per `references/agent-catalog.md`.
6. Decide whether explicit confirmation is needed:
   - When requirements are unclear, approaches diverge significantly, execution cost is high, or impact could be large → confirm with the user first.
   - When the user has already explicitly asked for team execution and the approach is clear with controllable risk → proceed directly to Phase 2.

### Phase 2: Team formation

1. Form the team based on the Phase 1 analysis:
   - `TeamCreate` — members reference the role definitions in the `agents/` directory.
2. `TaskCreate` to register subtasks:
   - Assign 3-6 tasks per agent.
   - Use `depends_on` to declare task dependencies.
3. Create the `_workspace/` directory to store intermediate artifacts.

### Phase 3: Execution

1. Members claim and execute tasks via the shared task list.
2. Members coordinate in real time via `SendMessage`:
   - Share findings, discuss conflicts, fill in gaps.
   - They can communicate directly without going through the Leader.
3. The Leader monitors progress via `TaskGet` and steps in to coordinate when necessary.
4. Artifacts are saved to `_workspace/{phase}_{agent}_{artifact}.{ext}`.

### Phase 4: Integration and verification

1. Collect every member's artifacts via `Read`.
2. Check consistency:
   - Do both sides of an interface definition match?
   - Are there contradictions between artifacts?
3. Produce the final artifact.
4. Brief quality verification.

### Phase 5: Cleanup and reporting

1. Report completion status and the location of key artifacts to the user.
2. `TeamDelete` to clean up the team.
3. Keep `_workspace/` for auditing and follow-up tasks.

## Common team templates

### Feature development
```
architect(1) → developer(1-2) → reviewer(1) + tester(1)
Pattern: pipeline + generate-verify
```

### Technical research
```
researcher(2-4)
Pattern: fan-out/fan-in
```

### Code review
```
reviewer(2-3) (each focusing on security / performance / architecture)
Pattern: fan-out/fan-in
```

### Large-scale refactoring
```
project-lead(1) + developer(2-3)
Pattern: supervisor
```

### Full-stack development
```
architect(1) + developer-frontend(1) + developer-backend(1) + tester(1)
Pattern: hierarchical delegation
```

### Documentation improvement
```
tech-writer(1) + researcher(1)
Pattern: fan-out/fan-in
```

## Error handling

| Situation | Strategy |
|-----------|----------|
| A single member fails | Leader confirms via SendMessage → restart or create a replacement |
| More than half the members fail | Notify the user to confirm whether to continue |
| Timeout | Use the partial results already collected |
| Data conflict between members | Annotate the sources side by side; don't delete either one |
| Delayed task status | Leader confirms via TaskGet, then manually TaskUpdate |

## Data-passing conventions

| Strategy | Method | Applicable scenario |
|----------|--------|---------------------|
| Message | SendMessage | Real-time coordination, lightweight feedback |
| Task | TaskCreate/TaskUpdate | Progress tracking, dependency management |
| File | Write/Read `_workspace/` | Structured artifacts (>100 lines) |
| Return value | Agent tool return | Sub-agent result collection |

## Conflict-resolution protocol

1. Data conflict → don't delete either side; annotate the sources and list them side by side.
2. Design disagreement → the architect has the final say, but must explain the reasoning.
3. Implementation diverges from design → the developer reports to the architect, who makes the call.

## Test scenarios

### Normal flow: feature development
1. User requests "add user authentication to the project".
2. Phase 1 analysis → medium-sized feature development → pipeline pattern.
3. Phase 2 forms an architect + developer + reviewer team.
4. Phase 3 executes in order: design → implement → review.
5. Phase 4 integration.
6. Output: design doc + code + review report under `_workspace/`.

### Error flow: development blocked
1. During Phase 3 the developer hits an unclear interface definition.
2. The developer SendMessages the architect to request clarification.
3. The architect fills in the interface definition and SendMessages a reply.
4. The developer continues the implementation.

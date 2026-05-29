# Task decomposition methodology

When facing a complex development task, use the following 5 steps to systematically break it into executable subtasks.

## Step 1: Identify the nature of the task

Determine which type the task belongs to; different types have different default handling:

| Task type | Typical signals | Default pattern |
|-----------|-----------------|-----------------|
| New feature development | "add", "implement", "support" | Pipeline + generate-verify |
| Technical research | "research", "compare", "evaluate", "selection" | Fan-out/fan-in |
| Code review | "review", "check" | Fan-out/fan-in |
| Bug fix | "fix", "resolve" | Generate-verify |
| Refactor / migration | "refactor", "migrate", "upgrade", "replace" | Supervisor |
| Documentation | "docs", "README", "API doc" | Fan-out/fan-in |
| Full-stack project | "build", "full-stack", "from scratch" | Hierarchical delegation |

## Step 2: Size estimation

Count the number of independent concerns in the task:

```
How to identify concerns:
1. List all the modules/domains that need to be handled.
2. Identify the parts that require different expertise.
3. Find the sub-goals that can be verified independently.

Verdict:
- 1-2 concerns → small → no team, sub-agent or do it directly
- 3-5 concerns → medium → 2-3 person team
- 6+ concerns  → large → 3-5 person team
```

**Examples**:
- "Add a login feature" → 3 concerns (auth logic, frontend pages, security) → medium.
- "Research CLI frameworks" → 2 concerns (feature comparison, community reception) → small.
- "Full-stack e-commerce system" → 7+ concerns → large.

## Step 3: Pattern matching

Based on the results of Steps 1-2, pick an architecture pattern per `pattern-selector.md`.

**Quick decision path:**
```
Small task?
├─ Yes → no team, use a sub-agent directly
└─ No
    ├─ Strong dependencies between subtasks? → pipeline
    ├─ Subtasks can run independently in parallel? → fan-out/fan-in
    ├─ Need to verify after generating?          → generate-verify
    ├─ Workload dynamic and uncertain?           → supervisor
    └─ Naturally multi-level structure?          → hierarchical delegation
```

## Step 4: Role selection

Pick a combination from the role library per `agent-catalog.md`.

**Selection principles:**
1. **Necessity** — each role must make an irreplaceable specialized contribution.
2. **Minimization** — don't use 5 people for what 3 can do.
3. **Coverage** — ensure every critical part of the task has a role responsible for it.
4. **Reusability** — the same role can appear multiple times (e.g., 2 researchers each researching a different dimension).

**Role instantiation:**
When the same role needs multiple instances, distinguish them by name:
- `developer-frontend` / `developer-backend`
- `reviewer-security` / `reviewer-performance`
- `researcher-frameworks` / `researcher-community`

## Step 5: Subtask decomposition

Break the overall task into concrete subtasks for each agent.

**Decomposition principles:**
1. Each subtask has a clear **input** and **output**.
2. **Dependencies** between subtasks are declared explicitly (with `depends_on`).
3. Parallelize whatever can be parallelized.
4. Assign **3-6 tasks** per agent (too few makes the role redundant; too many makes the granularity too fine).
5. Each subtask should be **independently verifiable**.

**Subtask template:**
```
Task name: {verb + noun}
Assigned to: {agent name}
Input: {dependent upstream artifacts or raw input}
Output: {artifact path and format}
Dependencies: {list of upstream task IDs}
Acceptance criteria: {how to tell it's done}
```

**Example — new feature development (user authentication):**

| # | Task | Agent | Dependencies | Artifacts |
|---|------|-------|--------------|-----------|
| 1 | Analyze auth requirements and security requirements | architect | — | `01_architect_design.md` |
| 2 | Design auth interfaces and data models | architect | 1 | `01_architect_design.md` (updated) |
| 3 | Implement the auth backend logic | developer | 2 | code + `02_developer_changelog.md` |
| 4 | Implement the login/registration frontend pages | developer | 2 | code + `02_developer_changelog.md` |
| 5 | Review security and code quality | reviewer | 3,4 | `03_reviewer_report.md` |
| 6 | Write auth-flow tests | tester | 3,4 | test code + `04_tester_report.md` |
| 7 | Revise per review comments | developer | 5 | code update |

## Data-flow design

Determine the data flow direction and passing method between each stage:

```
[architect]
    ↓ _workspace/01_architect_design.md
[developer]
    ↓ code + _workspace/02_developer_changelog.md
[reviewer]
    ↓ _workspace/03_reviewer_report.md
[developer]
    ↓ revise the code
[tester]
    ↓ test code + _workspace/04_tester_report.md
```

**Data-passing conventions:**
- All roles pass data through `_workspace/` files.
- An upstream role's artifact is the downstream role's input.
- File naming convention: `{phase number}_{role name}_{artifact name}.{ext}`

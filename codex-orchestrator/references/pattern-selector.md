# Architecture pattern selection guide

## The 6 architecture patterns

### 1. Pipeline
```
[A] → [B] → [C] → [D]
```
- **Characteristics**: strong dependency between stages; each stage's output is the next stage's input.
- **Use for**: new feature development (design→implement→review→test), ETL, CI/CD.
- **Pros**: clear flow; each stage has a well-defined deliverable.
- **Cons**: serial execution; an upstream blocker affects the whole chain.

### 2. Fan-out/Fan-in
```
        ┌→ [A] →┐
[input] →├→ [B] →├→ [aggregate]
        └→ [C] →┘
```
- **Characteristics**: multiple agents process independently in parallel, then results are aggregated.
- **Use for**: technical research, multi-dimensional code review, competitive analysis.
- **Pros**: parallel execution, high efficiency.
- **Cons**: the aggregation step must handle contradictions and overlaps.

### 3. Expert Pool
```
[router] → by input type → [expert A]
                          → [expert B]
                          → [expert C]
```
- **Characteristics**: selectively invoke different experts based on the input's features.
- **Use for**: mixed-type tasks, multi-language projects, modules on different tech stacks.
- **Pros**: precise matching of specialized capabilities.
- **Cons**: requires accurate routing decisions.

### 4. Producer-Reviewer (generate-verify)
```
[producer] → artifact → [reviewer] → PASS/FIX
                                       ↓ FIX
                                    [producer] → revise → [reviewer] (at most 2 rounds)
```
- **Characteristics**: one side produces, the other verifies, iterating to improve.
- **Use for**: code writing + review, doc writing + proofreading, design + review.
- **Pros**: built-in quality assurance.
- **Cons**: the number of iterations must be controlled (recommended: at most 2 rounds).

### 5. Supervisor
```
[supervisor]
  ├→ assign task → [member A]
  ├→ assign task → [member B]
  └→ dynamic reassignment (based on progress and member status)
```
- **Characteristics**: a central agent manages state and dynamically assigns tasks.
- **Use for**: large-scale refactoring/migration, batch processing with uncertain workload.
- **Pros**: dynamic load balancing, adapts to change.
- **Cons**: the supervisor is a single point; decision quality depends on its capability.

### 6. Hierarchical Delegation
```
[overall lead]
  ├→ [frontend lead]
  │    ├→ [UI development]
  │    └→ [state management]
  └→ [backend lead]
       ├→ [API development]
       └→ [data layer]
```
- **Characteristics**: top-down recursive decomposition and delegation.
- **Use for**: full-stack projects, large systems, multi-level organizations.
- **Pros**: maps naturally onto complex system structures.
- **Cons**: too many levels increases communication overhead.

## Decision matrix

| Dimension | Pipeline | Fan-out/Fan-in | Expert Pool | Generate-Verify | Supervisor | Hierarchical |
|-----------|----------|----------------|-------------|-----------------|------------|--------------|
| Inter-stage dependency | Strong | Weak | None | Bidirectional | Weak | Tree-shaped |
| Parallelism | Low | High | Medium | Low | Medium | Medium |
| Suitable team size | 2-4 | 2-5 | 1+N | 2 | 1+2-3 | 3-7 |
| Communication overhead | Low | Low | Low | Medium | Medium | High |
| Quality assurance | Needs extra mechanism | At aggregation | Depends on routing | Built-in | Depends on supervisor | Layered review |

## Codex execution-action mapping

| Pattern | How to execute in Codex | Fallback when true parallelism isn't suitable |
|---------|-------------------------|-----------------------------------------------|
| Pipeline | Execute roles one by one in order; write each stage's artifact to `_workspace/` | The current session plays each role serially |
| Fan-out/Fan-in | When parallel is possible, have different roles each produce a file, then aggregate them together | Complete several independent branches one after another, then aggregate together |
| Expert Pool | Make the routing decision first, then invoke only the 1-N roles that match | The current session executes the matched roles one by one per the routing result |
| Generate-Verify | developer / tech-writer alternates with reviewer / tester, at most 2 rounds | The current session strictly follows the "generate → verify → fix" loop |
| Supervisor | project-lead writes the plan first, then drives several executing roles forward in batches | The project-lead plan stays the same; the current session pushes forward serially in batches |
| Hierarchical Delegation | Produce the overall design first, then split into frontend/backend or module leads executing in parallel/batches | Keep the hierarchical split, but switch execution to serial, staged progress |

## Execution-mode selection

```
How many roles are needed?
├─ 1 → execute a single role directly
└─ 2+
    ├─ Are there ordering dependencies between roles?
    │   ├─ Yes → sequential execution (pipeline)
    │   └─ No → parallel execution (fan-out/fan-in)
    └─ Need iterative improvement?
        └─ Yes → iterative execution (generate-verify, at most 2 rounds)
```

### Data-passing method
All roles pass data through `_workspace/` files:
- An upstream role writes the artifact file.
- A downstream role reads the upstream artifact as input.
- File naming convention: `{phase number}_{role name}_{artifact name}.{ext}`

### Additional selection rules
- As long as the task can still be completed at high quality by a single role, don't force a role split just for "orchestration for its own sake".
- "Parallel execution" is an optimization, not a prerequisite; when you can't parallelize safely, prioritize keeping role boundaries and artifacts clear.
- When selecting a pattern, look at dependencies and verification needs first, then consider whether parallelism is worth it.

## Common composite patterns

| Scenario | Combination | Notes |
|----------|-------------|-------|
| Research + development | Fan-out/Fan-in → Pipeline | Research in parallel first, then develop serially |
| Development + review | Pipeline + Generate-Verify | After development, enter the review iteration |
| Full-stack + QA | Hierarchical Delegation + Fan-out/Fan-in | Frontend and backend developed in parallel, QA reviews in parallel |
| Refactor + test | Supervisor + Generate-Verify | Dynamically assign refactoring tasks, verify each batch |

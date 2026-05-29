# Agent role quick reference

## Role overview

| Role | File | Core capabilities | Artifacts |
|------|------|-------------------|-----------|
| architect | `agents/architect.md` | Requirements analysis, module decomposition, interface definition, technology selection | `01_architect_design.md` |
| developer | `agents/developer.md` | Code implementation, bug fixing, following project conventions | code + `02_developer_changelog.md` |
| reviewer | `agents/reviewer.md` | Reviewing architectural consistency, security, performance, code quality | `03_reviewer_report.md` |
| tester | `agents/tester.md` | Test design, boundary verification, defect reporting | test code + `04_tester_report.md` |
| researcher | `agents/researcher.md` | Multi-source research, comparing approaches, recommendations | `00_researcher_{topic}_findings.md` |
| tech-writer | `agents/tech-writer.md` | API docs, usage guides, README | `05_techwriter_docs.md` |
| project-lead | `agents/project-lead.md` | Task decomposition, team formation, progress monitoring, conflict resolution | `00_project_lead_plan.md` |

## Quick selection by scenario

### New feature development
```
architect + developer + reviewer [+ tester]
Pattern: pipeline + generate-verify
Flow: architect designs → developer implements → reviewer reviews → tester verifies
```

### Technical research / selection
```
researcher × 2-4 (each focusing on a different dimension)
Pattern: fan-out/fan-in
Flow: parallel research → aggregate and compare → recommendation
```

### Code review
```
reviewer × 2-3 (one perspective each for security / performance / architecture)
Pattern: fan-out/fan-in
Flow: parallel review → aggregated report (sorted by severity)
```

### Large-scale refactoring / migration
```
project-lead + developer × 2-3
Pattern: supervisor
Flow: project-lead analyzes → assigns in batches → dynamically reassigns → verifies batch by batch
```

### Full-stack project
```
architect + developer(frontend) + developer(backend) + tester
Pattern: hierarchical delegation
Flow: architect does the overall design → frontend and backend developed in parallel → tester runs integration tests
```

### Documentation improvement
```
tech-writer + researcher
Pattern: fan-out/fan-in
Flow: researcher gathers information → tech-writer writes the docs
```

### Bug fix / investigation
```
developer + tester
Pattern: generate-verify
Flow: developer fixes → tester verifies → iterate (at most 2 rounds)
```

### Project bootstrap
```
researcher + architect + developer
Pattern: pipeline
Flow: researcher investigates → architect designs → developer builds the skeleton
```

## Inter-role communication matrix

Arrows indicate the direction of the active sender; the content is the typical message type:

```
architect ──architecture design, interface definition──→ developer
architect ──review focus points───────────────────────→ reviewer
architect ──critical paths────────────────────────────→ tester
developer ──design issues──────────────────────────────→ architect
developer ──ready-for-review notice────────────────────→ reviewer
developer ──testing needs──────────────────────────────→ tester
reviewer  ──review comments────────────────────────────→ developer
reviewer  ──architecture issues────────────────────────→ architect
reviewer  ──risk points────────────────────────────────→ tester
tester    ──bug reports────────────────────────────────→ developer
researcher ──research conclusions──────────────────────→ architect
tech-writer ──accuracy-review request──────────────────→ reviewer
```

## Team-size guide

| Task size | Recommended headcount | Tasks per person |
|-----------|-----------------------|------------------|
| Small (1-2 concerns) | No team | — |
| Medium (3-5 concerns) | 2-3 people | 3-5 |
| Large (6+ concerns) | 3-5 people | 4-6 |

**Principle**: 3 focused members > 5 scattered members. Quality over quantity.

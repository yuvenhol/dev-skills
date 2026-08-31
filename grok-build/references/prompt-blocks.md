# Prompt blocks

Use these blocks selectively. Wrap each in the XML tag in its heading.

## `task`

```xml
<task>
Describe the concrete job, the relevant repository or failure context, and the expected end state.
</task>
```

## `structured_output_contract`

```xml
<structured_output_contract>
Return exactly the requested output shape and nothing else.
Keep the answer compact.
Put the highest-value findings or decisions first.
</structured_output_contract>
```

## `compact_output_contract`

```xml
<compact_output_contract>
Keep the final answer compact and structured.
Do not include long scene-setting or repeated recap.
</compact_output_contract>
```

## `default_follow_through_policy`

```xml
<default_follow_through_policy>
Default to the most reasonable low-risk interpretation and keep going.
Only stop to ask questions when a missing detail changes correctness, safety, or an irreversible action.
</default_follow_through_policy>
```

## `completeness_contract`

```xml
<completeness_contract>
Resolve the task fully before stopping.
Do not stop at the first plausible answer.
Check whether there are follow-on fixes, edge cases, or cleanup needed for a correct result.
</completeness_contract>
```

## `verification_loop`

```xml
<verification_loop>
Before finalizing, verify the result against the task requirements and the changed files or tool outputs.
If a check fails, revise the answer instead of reporting the first draft.
</verification_loop>
```

## `missing_context_gating`

```xml
<missing_context_gating>
Do not guess missing repository facts.
If required context is absent, retrieve it with tools or state exactly what remains unknown.
</missing_context_gating>
```

## `grounding_rules`

```xml
<grounding_rules>
Ground every claim in the provided context or your tool outputs.
Do not present inferences as facts.
If a point is a hypothesis, label it clearly.
</grounding_rules>
```

## `citation_rules`

```xml
<citation_rules>
Back important claims with citations or explicit references to the source material you inspected.
Prefer primary sources.
</citation_rules>
```

## `action_safety`

```xml
<action_safety>
Keep changes tightly scoped to the stated task.
Avoid unrelated refactors, renames, or cleanup unless they are required for correctness.
Call out any risky or irreversible action before taking it.
</action_safety>
```

## `research_mode`

```xml
<research_mode>
Separate observed facts, reasoned inferences, and open questions.
Prefer breadth first, then go deeper only where the evidence changes the recommendation.
</research_mode>
```

## `dig_deeper_nudge`

```xml
<dig_deeper_nudge>
After you find the first plausible issue, check for second-order failures, empty-state behavior, retries, stale state, and rollback paths before you finalize.
</dig_deeper_nudge>
```

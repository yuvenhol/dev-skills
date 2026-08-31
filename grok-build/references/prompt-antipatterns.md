# Prompt anti-patterns

Avoid these when prompting Grok Build.

## Vague task framing

Bad: `Take a look at this and let me know what you think.`

Better:

```xml
<task>
Review this change for material correctness and regression risks.
</task>
```

## Missing output contract

Bad: `Investigate and report back.`

Better:

```xml
<structured_output_contract>
Return:
1. root cause
2. evidence
3. smallest safe next step
</structured_output_contract>
```

## No follow-through default

Bad: `Debug this failure.`

Better:

```xml
<default_follow_through_policy>
Keep going until you have enough evidence to identify the root cause confidently.
</default_follow_through_policy>
```

## Asking for more reasoning instead of a better contract

Bad: `Think harder and be very smart.`

Better:

```xml
<verification_loop>
Before finalizing, verify that the answer matches the observed evidence and task requirements.
</verification_loop>
```

## Mixing unrelated jobs into one run

Bad: `Review this diff, fix the bug you find, update the docs, and suggest a roadmap.`

Better: run `review` first, then a separate `run --write` for the fix, then docs
if still needed.

## Unsupported certainty

Bad: `Tell me exactly why production failed.`

Better:

```xml
<grounding_rules>
Ground every claim in the provided context or tool outputs.
If a point is an inference, label it clearly.
</grounding_rules>
```

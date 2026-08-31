# Grok Build prompting

Use this when composing the prompt passed to `run`. Review and critique already
have templates in `prompts/`. Do not use this skill to inspect the repo or
solve the task.

Prompt Grok like an operator, not a collaborator. Keep prompts compact and
block-structured with XML tags. State the task, the output contract, the
follow-through default, and the few extra constraints that matter.

Core rules:

- One clear task per run. Split unrelated asks.
- Say what done looks like.
- Add grounding and verification where unsupported guesses would hurt.
- Prefer a tighter contract over raising `--effort`.
- Use the XML tag names from `prompt-blocks.md`.

Default recipe:

- `<task>`
- `<structured_output_contract>` or `<compact_output_contract>`
- `<default_follow_through_policy>`
- `<verification_loop>` or `<completeness_contract>` for debug/fix
- `<grounding_rules>` for review/research
- `<action_safety>` when `--write` is on

Assembly:

1. Exact task and scope in `<task>`.
2. Smallest output contract the host can use.
3. Keep going by default, or stop only for high-risk missing details.
4. Add verification, grounding, and safety only where needed.
5. Delete redundant instructions before sending.

`run --resume-last` should send only the delta instruction unless the direction
changed.

Blocks: `prompt-blocks.md`.
Templates: `prompt-recipes.md`.
What not to do: `prompt-antipatterns.md`.

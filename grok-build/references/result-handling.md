# Grok Build result handling

When the helper returns Grok output:

- Preserve verdict, summary, findings, and next-steps structure.
- For review or critique, present findings first, ordered by severity.
- Use file paths and line numbers exactly as reported.
- Keep evidence boundaries. If Grok marked an inference, uncertainty, or
  follow-up question, keep that distinction.
- If there are no findings, say so explicitly. Keep residual-risk notes brief.
- If Grok made edits, say so and list touched files when the helper provides them.
- For delegate/`run`: do not turn a failed or incomplete Grok run into a
  host-side implementation attempt. Report the failure and stop.
- For delegate/`run`: if Grok was never successfully invoked, do not generate a
  substitute answer.
- After presenting review or critique findings, STOP. Do not make code changes.
  Ask which issues, if any, the user wants fixed. Auto-applying review fixes is
  forbidden even when the fix looks obvious.
- If the helper reports malformed output or a failed run, include the most
  actionable stderr lines and stop instead of guessing.
- If setup or authentication is required, send the user to `check`. Do not
  invent an alternate auth flow.

When a background job starts, report the job id and how to call `status` /
`show` / `stop`. Do not wait on it in the same turn.

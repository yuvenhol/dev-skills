# Grok Build CLI runtime

Single source of truth for how this skill invokes Grok. The parent skill and
`agents/grok-delegate.md` point here; do not restate flag policy elsewhere.

Primary helper:

```bash
python3 "${SKILL_DIR}/scripts/grok_bridge.py" <command>
```

Do not call `grok` directly unless the bridge is broken and you are diagnosing
that failure.

## Environment

| Variable | Purpose |
|----------|---------|
| `GROK_BINARY` | Optional path to the `grok` executable |
| `GROK_HOME` | Config/state root (default `~/.grok`) |
| `XAI_API_KEY` | API-key auth when there is no `grok login` session |

Job state lives in `~/.grok/skill-bridge/<workspace-hash>/`.

## Commands

```text
check [--json]
review [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <m>] [--effort <e>]
critique [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <m>] [--effort <e>] [focus]
run [--background|--wait] [--write] [--resume-last|--resume|--fresh] [--model <m>] [--effort <e>] [--prompt-file <path>] [prompt]
run-resume-candidate [--json]
status [job-id] [--wait]
show [job-id]
stop [job-id]
```

`--cwd` defaults to the current workspace. Pass it when the host cwd is wrong.

## What the bridge actually runs

Read-only review / critique / research:

```bash
grok -p <prompt> --agent explore --always-approve --sandbox read-only --cwd <ws> --output-format json --no-auto-update
```

If a runtime socket deny path is a symlink (Docker Desktop on macOS:
`/var/run/docker.sock` → `~/.docker/run/docker.sock`), Grok 1.0.13 refuses
`--sandbox read-only` instead of masking the canonical target. The bridge
detects that, omits `--sandbox`, keeps `--agent explore`, and adds
`--disallowed-tools search_replace`. `check` reports `sandbox.readOnly`.

Critique adds `--json-schema` from `schemas/review-output.schema.json`.

Write-capable delegate (`run --write`):

```bash
grok -p <prompt> --always-approve --cwd <ws> --output-format json --no-auto-update
```

Resume:

```bash
grok -p <prompt> --resume <sessionId> ...
```

`--always-approve` is required in headless mode because there is no TUI to
click Approve. Read-only safety is `--sandbox read-only`, not permission
prompts. Headless `plan` mode without an approver can hang.

## Write policy

| Layer | Default |
|-------|---------|
| `review` / `critique` | Always read-only. Never pass `--write`. |
| `run` from the delegate agent | `--write` unless the user asked for read-only / review / diagnosis without edits / research without edits |
| Direct `run` without `--write` | Read-only sandbox |

## Routing flags (not task text)

Strip these from the natural-language prompt before passing it to `run`:

- `--background`, `--wait` — host execution mode
- `--model`, `--effort` — runtime selection
- `--resume`, `--resume-last`, `--fresh` — session routing
- `--write` — write policy

`--effort` values the CLI accepts: `none`, `minimal`, `low`, `medium`, `high`,
`xhigh`, `max`. If the user does not name one, omit it.

`--model`: omit unless the user names a model. Do not default to `grok-4.6`.

`--resume-last` continues the latest finished `run` job in this repo that has a
Grok `sessionId`. It is an error if a `run` job is still queued or running.

## Review target

- `auto` (default): dirty working tree → working-tree; else `--base` → branch
- `working-tree`: staged + unstaged + untracked
- `branch`: requires `--base <ref>`, uses `git diff <base>...HEAD`

`review` rejects extra focus text. `critique` uses leftover args as focus.

## One-shot rules

- One bridge invocation per handoff.
- Return stdout unchanged, then apply `result-handling.md`.
- If the helper says Grok is missing or unauthenticated, stop and tell the user
  to run `check`. Do not improvise another auth flow.
- If you are already Grok Build, do not use this runtime.

---
name: grok-build
description: >
  Delegate review, critique, diagnosis, or implementation to the local Grok Build
  CLI. Use when the user says grok, grok-build, grok -p, 交给 grok, ask Grok to
  review, Grok critique, rescue with Grok, or hand a coding task to Grok Build.
  Also use for /grok-build check, review, critique, delegate, status, show, stop.
  Do not use if you are already Grok Build — do the work yourself.
metadata:
  version: 1.0.0
---

# Grok Build — call the local `grok` CLI

Shell out to Grok Build the way the Codex Claude Code plugin shells out to Codex.
The only invocation path is `scripts/grok_bridge.py`. Do not invent `grok -p`
flags by hand.

If you are already running inside Grok Build, stop. Do the task with your own
tools. Do not spawn another `grok` process.

## Resolve the bridge

```bash
python3 "${SKILL_DIR}/scripts/grok_bridge.py" <command>
```

`SKILL_DIR` is the directory that contains this `SKILL.md`. If the host does not
set it, resolve it from the loaded skill path.

## Commands

| User ask | Bridge command |
|----------|----------------|
| check / setup / is grok ready | `check` |
| review current changes | `review` |
| critique / adversarial review / challenge the design | `critique` |
| delegate / rescue / ask grok to investigate or fix | `run` (via `agents/grok-delegate.md` when the host has subagents) |
| status / runs | `status` |
| result / show | `show` |
| cancel / stop | `stop` |

Flag and write-policy details live in `references/cli-runtime.md`.
Prompt contracts live in `references/prompting.md`.
How to present output lives in `references/result-handling.md`.

## Check

```bash
python3 "${SKILL_DIR}/scripts/grok_bridge.py" check --json
```

If Grok is missing, tell the user to install the CLI and put `grok` on PATH (or
set `GROK_BINARY`). If it is installed but not logged in, tell them to run
`grok login` or set `XAI_API_KEY`, then `grok models`. Do not invent an install
path.

## Review (read-only)

Review-only. Do not patch, fix, or offer to start editing.

```bash
python3 "${SKILL_DIR}/scripts/grok_bridge.py" review [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <model>] [--effort <low|medium|high>]
```

- `--wait` / `--background`: honor them. If neither is present, estimate size
  from `git status --short --untracked-files=all` plus `git diff --shortstat`
  (and `git diff --shortstat <base>...HEAD` for branch review). Recommend wait
  only for ~1–2 files; otherwise recommend background.
- `review` takes no extra focus text. For a steerable pass, use `critique`.

After review output: stop. Ask which findings, if any, to fix.

## Critique (read-only, steerable)

Same target selection as review. Extra positional text is the focus.

```bash
python3 "${SKILL_DIR}/scripts/grok_bridge.py" critique [--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <model>] [--effort <low|medium|high>] [focus text]
```

Same review-only constraint: present findings, then stop.

## Delegate

If the host can spawn a subagent, load `agents/grok-delegate.md` and forward the
raw request. Otherwise follow `references/cli-runtime.md` and run `run` yourself.

```bash
python3 "${SKILL_DIR}/scripts/grok_bridge.py" run [--background|--wait] [--write] [--resume-last|--fresh] [--model <model>] [--effort <low|medium|high>] [prompt]
```

Before a fresh run, unless the user already passed `--resume` / `--fresh`:

```bash
python3 "${SKILL_DIR}/scripts/grok_bridge.py" run-resume-candidate --json
```

If `available` is true, ask once: continue the current Grok thread, or start a
new one. Put the recommended option first. Follow-ups like "continue", "keep
going", "apply the top fix" recommend continue.

Write policy and resume routing are in `references/cli-runtime.md`.

Tighten the forwarded prompt with `references/prompting.md`. Do not solve the
task yourself and then call Grok.

## Status / show / stop

```bash
python3 "${SKILL_DIR}/scripts/grok_bridge.py" status [job-id]
python3 "${SKILL_DIR}/scripts/grok_bridge.py" show [job-id]
python3 "${SKILL_DIR}/scripts/grok_bridge.py" stop [job-id]
```

Do not poll `status` in a loop in this turn after a background launch. Tell the
user the job id and how to check it.

## Host notes

- Claude Code / Cursor / Codex: this skill is the entry point; the bridge owns
  PIDs and logs under `~/.grok/skill-bridge/`.
- Grok Build: ignore this skill and work in-session.
- Return bridge stdout verbatim for `review`, `critique`, and `run`. Then apply
  `references/result-handling.md`.

#!/usr/bin/env python3
"""Portable Grok Build bridge. Stdlib only.

Mirrors the command surface of openai/codex-plugin-cc and
xai-org/grok-build-plugin-cc, but shells out to `grok` directly so any
host (Claude Code, Cursor, Codex, Grok) can call it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = SKILL_ROOT / "prompts"
REVIEW_SCHEMA = SKILL_ROOT / "schemas" / "review-output.schema.json"
DEFAULT_CONTINUE_PROMPT = "Continue the previous task. Apply the next safest step."
VALID_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
MAX_REVIEW_CHARS = 180_000
CHECK_TIMEOUT_SEC = 30
RUNTIME_SOCKET_CANDIDATES = (
    Path("/var/run/docker.sock"),
    Path("/run/docker.sock"),
    Path("/var/run/podman.sock"),
    Path("/run/podman.sock"),
)
SANDBOX_APPLY_MARKERS = (
    "could not apply the '",
    "runtime-socket deny resolution failed",
    "endpoint is a symlink",
)


class BridgeError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def grok_binary() -> str:
    override = os.environ.get("GROK_BINARY", "").strip()
    if override:
        return override
    found = shutil.which("grok")
    if not found:
        raise BridgeError(
            "Grok CLI is not installed or not on PATH. Install it, or set GROK_BINARY."
        )
    return found


def grok_home() -> Path:
    override = os.environ.get("GROK_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".grok"


def run_cmd(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=check,
    )


def git_root(cwd: Path) -> Path:
    result = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if result.returncode != 0:
        raise BridgeError("Not a git repository. Review commands need git.")
    return Path(result.stdout.strip())


def workspace_id(cwd: Path) -> str:
    return hashlib.sha256(str(cwd.resolve()).encode()).hexdigest()[:16]


def state_dir(cwd: Path) -> Path:
    path = grok_home() / "skill-bridge" / workspace_id(cwd)
    path.mkdir(parents=True, exist_ok=True)
    (path / "jobs").mkdir(exist_ok=True)
    (path / "logs").mkdir(exist_ok=True)
    marker = path / "workspace"
    if not marker.exists():
        marker.write_text(str(cwd.resolve()) + "\n")
    return path


def atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json(path: Path, data: Any) -> None:
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def job_path(cwd: Path, job_id: str) -> Path:
    return state_dir(cwd) / "jobs" / f"{job_id}.json"


def log_path(cwd: Path, job_id: str) -> Path:
    return state_dir(cwd) / "logs" / f"{job_id}.log"


def list_jobs(cwd: Path) -> list[dict[str, Any]]:
    jobs_dir = state_dir(cwd) / "jobs"
    jobs = []
    for path in sorted(jobs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            jobs.append(read_json(path))
        except (OSError, json.JSONDecodeError):
            continue
    return jobs


def save_job(cwd: Path, job: dict[str, Any]) -> dict[str, Any]:
    job["updatedAt"] = now_iso()
    write_json(job_path(cwd, job["id"]), job)
    return job


def load_job(cwd: Path, job_id: str) -> dict[str, Any]:
    path = job_path(cwd, job_id)
    if not path.exists():
        raise BridgeError(f"No stored job found for {job_id}.")
    return read_json(path)


def new_job_id(kind: str) -> str:
    return f"{kind}-{uuid.uuid4().hex[:8]}"


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def refresh_job(cwd: Path, job: dict[str, Any]) -> dict[str, Any]:
    if job.get("status") in {"queued", "running"} and not pid_alive(job.get("pid")):
        job["status"] = "failed"
        job["errorMessage"] = job.get("errorMessage") or "Process exited without a terminal status."
        job["finishedAt"] = job.get("finishedAt") or now_iso()
        save_job(cwd, job)
    return job


def interpolate(template: str, values: dict[str, str]) -> str:
    text = template
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def first_line(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return fallback


def grok_available() -> dict[str, Any]:
    try:
        binary = grok_binary()
    except BridgeError as exc:
        return {"available": False, "binary": None, "version": None, "error": str(exc)}
    try:
        result = run_cmd([binary, "--version"], cwd=Path.cwd(), timeout=CHECK_TIMEOUT_SEC)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "binary": binary, "version": None, "error": str(exc)}
    version = (result.stdout or result.stderr).strip().splitlines()
    return {
        "available": result.returncode == 0,
        "binary": binary,
        "version": version[0] if version else None,
        "error": None if result.returncode == 0 else (result.stderr or result.stdout).strip(),
    }


def require_grok() -> str:
    status = grok_available()
    if not status["available"]:
        raise BridgeError(status.get("error") or "Grok CLI is not available.")
    return str(status["binary"])


def docker_host_socket() -> Path | None:
    host = os.environ.get("DOCKER_HOST", "").strip()
    if host.startswith("unix://"):
        return Path(host[len("unix://") :])
    return None


def inspect_runtime_socket(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"path": str(path)}
    try:
        lexists = path.is_symlink() or path.exists()
    except OSError as exc:
        info.update(status="unreadable", error=str(exc))
        return info
    if not lexists:
        info["status"] = "missing"
        return info
    if path.is_symlink():
        try:
            target = os.readlink(path)
        except OSError as exc:
            info.update(status="endpoint-symlink", error=str(exc))
            return info
        resolved = os.path.realpath(path)
        info.update(
            status="endpoint-symlink",
            target=target,
            resolved=resolved,
            targetExists=os.path.exists(resolved),
        )
        return info
    info["status"] = "socket" if path.exists() else "missing"
    return info


def runtime_socket_reports() -> list[dict[str, Any]]:
    seen: set[str] = set()
    reports = []
    extra = docker_host_socket()
    for path in (*RUNTIME_SOCKET_CANDIDATES, *([extra] if extra else [])):
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        reports.append(inspect_runtime_socket(path))
    return reports


def read_only_sandbox_block_reason(reports: list[dict[str, Any]] | None = None) -> str | None:
    """Grok 1.0.13 fails closed if a runtime-socket deny path is a symlink.

    Docker Desktop on macOS always makes /var/run/docker.sock a symlink to
    ~/.docker/run/docker.sock (often dangling). The CLI refuses --sandbox
    read-only instead of denying the canonical target.
    """
    for report in reports if reports is not None else runtime_socket_reports():
        if report.get("status") == "endpoint-symlink":
            target = report.get("target") or report.get("resolved") or "unknown"
            return (
                f"{report['path']} is a symlink to {target}; "
                "Grok cannot apply the read-only sandbox profile"
            )
    return None


def grok_auth(cwd: Path) -> dict[str, Any]:
    try:
        binary = grok_binary()
    except BridgeError as exc:
        return {"loggedIn": False, "error": str(exc)}
    try:
        result = run_cmd([binary, "models"], cwd=cwd, timeout=CHECK_TIMEOUT_SEC)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"loggedIn": False, "error": str(exc)}
    combined = (result.stdout or "") + (result.stderr or "")
    logged_in = result.returncode == 0 and "Available models" in combined
    return {
        "loggedIn": logged_in,
        "error": None if logged_in else first_line(combined, "grok models failed"),
    }


def handle_check(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    grok = grok_available()
    auth = grok_auth(cwd) if grok["available"] else {"loggedIn": False, "error": grok.get("error")}
    next_steps = []
    if not grok["available"]:
        next_steps.append("Install the Grok Build CLI and ensure `grok` is on PATH (or set GROK_BINARY).")
    elif not auth["loggedIn"]:
        next_steps.append("Authenticate with `grok login` (or set XAI_API_KEY), then verify with `grok models`.")
    sockets = runtime_socket_reports()
    sandbox_reason = read_only_sandbox_block_reason(sockets)
    sandbox = {
        "readOnly": "blocked" if sandbox_reason else "ok",
        "reason": sandbox_reason,
        "sockets": sockets,
        "fallback": "omit --sandbox; keep --agent explore for review/critique",
    }
    if sandbox_reason:
        next_steps.append(
            "read-only sandbox is blocked by a runtime-socket symlink; "
            "review/critique will skip --sandbox and stay read-only via the explore agent."
        )
    report = {
        "ready": bool(grok["available"] and auth["loggedIn"]),
        "grok": grok,
        "auth": auth,
        "sandbox": sandbox,
        "nextSteps": next_steps,
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["ready"] else 1
    lines = [
        f"Grok CLI: {'ok' if grok['available'] else 'missing'} ({grok.get('binary') or 'not found'})",
        f"Auth: {'ok' if auth['loggedIn'] else 'not logged in'}",
        f"Sandbox read-only: {sandbox['readOnly']}"
        + (f" ({sandbox_reason})" if sandbox_reason else ""),
        f"Ready: {'yes' if report['ready'] else 'no'}",
    ]
    if grok.get("version"):
        lines.insert(1, f"Version: {grok['version']}")
    if next_steps:
        lines.append("Next:")
        lines.extend(f"- {step}" for step in next_steps)
    print("\n".join(lines))
    return 0 if report["ready"] else 1


def git_output(argv: list[str], cwd: Path) -> str:
    result = run_cmd(argv, cwd=cwd)
    if result.returncode != 0:
        raise BridgeError(result.stderr.strip() or f"git command failed: {' '.join(argv)}")
    return result.stdout


def resolve_review_target(cwd: Path, *, base: str | None, scope: str) -> dict[str, str]:
    status = git_output(["git", "status", "--short", "--untracked-files=all"], cwd)
    dirty = bool(status.strip())
    resolved_scope = scope
    if scope == "auto":
        resolved_scope = "working-tree" if dirty or not base else "branch"
    if resolved_scope == "branch":
        if not base:
            raise BridgeError("--scope branch requires --base <ref>.")
        return {
            "scope": "branch",
            "base": base,
            "label": f"branch vs {base}",
        }
    return {
        "scope": "working-tree",
        "base": "",
        "label": "working tree (staged, unstaged, untracked)",
    }


def collect_review_context(cwd: Path, target: dict[str, str]) -> dict[str, str]:
    repo = git_root(cwd)
    branch = git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).strip()
    status = git_output(["git", "status", "--short", "--untracked-files=all"], cwd=repo)
    if target["scope"] == "branch":
        diff = git_output(["git", "diff", f"{target['base']}...HEAD"], cwd=repo)
        guidance = (
            f"Review the merge diff of HEAD against {target['base']}. "
            "Ignore unrelated working-tree noise."
        )
    else:
        cached = git_output(["git", "diff", "--cached"], cwd=repo)
        unstaged = git_output(["git", "diff"], cwd=repo)
        untracked_names = [
            line[3:]
            for line in status.splitlines()
            if line.startswith("?? ")
        ]
        untracked_blobs = []
        for name in untracked_names[:40]:
            path = repo / name
            if path.is_file() and path.stat().st_size <= 200_000:
                try:
                    untracked_blobs.append(f"--- untracked: {name}\n{path.read_text(encoding='utf-8', errors='replace')}")
                except OSError:
                    continue
        diff = "\n\n".join(part for part in (cached, unstaged, "\n\n".join(untracked_blobs)) if part.strip())
        guidance = "Review staged, unstaged, and untracked files in the working tree."
    content = (
        f"Repo: {repo}\nBranch: {branch}\nTarget: {target['label']}\n\n"
        f"git status:\n{status or '(clean)'}\n\n"
        f"diff:\n{diff or '(empty)'}\n"
    )
    if len(content) > MAX_REVIEW_CHARS:
        content = content[:MAX_REVIEW_CHARS] + "\n\n[truncated]\n"
        guidance += " The collected diff was truncated; inspect remaining files with tools."
    return {
        "repoRoot": str(repo),
        "branch": branch,
        "summary": first_line(status, target["label"]),
        "collectionGuidance": guidance,
        "content": content,
    }


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise BridgeError(f"Missing prompt template: {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, target: dict[str, str], context: dict[str, str], focus: str) -> str:
    return interpolate(
        load_prompt(name),
        {
            "TARGET_LABEL": target["label"],
            "USER_FOCUS": focus or "No extra focus provided.",
            "REVIEW_COLLECTION_GUIDANCE": context["collectionGuidance"],
            "REVIEW_INPUT": context["content"],
        },
    )


def sandbox_apply_failed(stderr: str) -> bool:
    text = stderr.lower()
    return any(marker.lower() in text for marker in SANDBOX_APPLY_MARKERS)


def build_grok_argv(
    *,
    prompt: str,
    cwd: Path,
    model: str | None,
    effort: str | None,
    write: bool,
    resume: str | None,
    structured: bool,
    agent: str | None,
    sandbox: str | None,
) -> list[str]:
    argv = [grok_binary(), "-p", prompt, "--cwd", str(cwd), "--always-approve", "--no-auto-update"]
    if agent:
        argv.extend(["--agent", agent])
    if sandbox:
        argv.extend(["--sandbox", sandbox])
    elif not write:
        argv.extend(["--disallowed-tools", "search_replace"])
    if model:
        argv.extend(["-m", model])
    if effort:
        argv.extend(["--effort", effort])
    if resume:
        argv.extend(["--resume", resume])
    if structured:
        argv.extend(["--json-schema", REVIEW_SCHEMA.read_text(encoding="utf-8")])
    else:
        argv.extend(["--output-format", "json"])
    return argv


def parse_grok_json(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {"text": text}
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {"text": text}
    if isinstance(data, dict):
        return data
    return {"text": text}


def append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{now_iso()} {line.rstrip()}\n")


def execute_grok(job: dict[str, Any], cwd: Path) -> dict[str, Any]:
    request = job["request"]
    write = bool(request.get("write"))
    sandbox: str | None = None if write else "read-only"
    skip_reason = None if write else read_only_sandbox_block_reason()
    if skip_reason:
        sandbox = None
        job["sandboxSkipReason"] = skip_reason
    argv = build_grok_argv(
        prompt=request["prompt"],
        cwd=cwd,
        model=request.get("model"),
        effort=request.get("effort"),
        write=write,
        resume=request.get("resumeSessionId"),
        structured=bool(request.get("structured")),
        agent=request.get("agent"),
        sandbox=sandbox,
    )
    log_file = Path(job["logFile"])
    append_log(log_file, f"start sandbox={sandbox or 'off'} {' '.join(argv[:4])} ...")
    if skip_reason:
        append_log(log_file, f"skip read-only sandbox: {skip_reason}")
    env = os.environ.copy()
    env["GROK_DISABLE_AUTOUPDATER"] = "1"
    proc = subprocess.Popen(
        argv,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    job["status"] = "running"
    job["pid"] = proc.pid
    job["sandbox"] = sandbox
    job["startedAt"] = job.get("startedAt") or now_iso()
    save_job(cwd, job)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0 and sandbox and sandbox_apply_failed(stderr or ""):
        append_log(log_file, f"sandbox apply failed; retrying without sandbox: {first_line(stderr, 'unknown')}")
        sandbox = None
        job["sandbox"] = None
        job["sandboxSkipReason"] = first_line(stderr, "sandbox apply failed")
        argv = build_grok_argv(
            prompt=request["prompt"],
            cwd=cwd,
            model=request.get("model"),
            effort=request.get("effort"),
            write=write,
            resume=request.get("resumeSessionId"),
            structured=bool(request.get("structured")),
            agent=request.get("agent"),
            sandbox=None,
        )
        proc = subprocess.Popen(
            argv,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        job["pid"] = proc.pid
        save_job(cwd, job)
        stdout, stderr = proc.communicate()
    parsed = parse_grok_json(stdout)
    text = parsed.get("text") or stdout
    session_id = parsed.get("sessionId") or parsed.get("threadId")
    job["exitStatus"] = proc.returncode
    job["sessionId"] = session_id
    job["stdout"] = text
    job["stderr"] = stderr
    job["finishedAt"] = now_iso()
    job["status"] = "completed" if proc.returncode == 0 else "failed"
    if proc.returncode != 0 and not job.get("errorMessage"):
        job["errorMessage"] = first_line(stderr or text, f"grok exited {proc.returncode}")
    save_job(cwd, job)
    append_log(
        log_file,
        f"status={job['status']} exit={proc.returncode} session={session_id or '-'} sandbox={sandbox or 'off'}",
    )
    return job


def render_job(job: dict[str, Any]) -> str:
    parts = [job.get("stdout") or ""]
    if job.get("status") == "failed":
        err = (job.get("stderr") or job.get("errorMessage") or "").strip()
        if err:
            parts.append(err)
    session_id = job.get("sessionId")
    if session_id:
        parts.append(f"\nGrok session ID: {session_id}\nResume: grok -p \"continue\" --resume {session_id}")
    parts.append(f"\nJob {job['id']} ({job.get('status')})")
    return "\n".join(part.rstrip() for part in parts if part).rstrip() + "\n"


def output_job(job: dict[str, Any], as_json: bool, *, exit_from_status: bool = True) -> int:
    if as_json:
        print(json.dumps(job, indent=2, ensure_ascii=False))
    else:
        sys.stdout.write(render_job(job))
    if not exit_from_status:
        return 0
    return 0 if job.get("status") == "completed" else 1


def spawn_worker(cwd: Path, job_id: str) -> int:
    cmd = [sys.executable, str(Path(__file__).resolve()), "_worker", "--cwd", str(cwd), "--job-id", job_id]
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return proc.pid


def create_job(
    cwd: Path,
    *,
    kind: str,
    title: str,
    summary: str,
    request: dict[str, Any],
    write: bool = False,
) -> dict[str, Any]:
    job_id = new_job_id(kind)
    job = {
        "id": job_id,
        "kind": kind,
        "title": title,
        "summary": summary,
        "status": "queued",
        "workspaceRoot": str(cwd.resolve()),
        "write": write,
        "pid": None,
        "sessionId": None,
        "logFile": str(log_path(cwd, job_id)),
        "createdAt": now_iso(),
        "request": request,
    }
    return save_job(cwd, job)


def enqueue_or_run(cwd: Path, job: dict[str, Any], *, background: bool, as_json: bool) -> int:
    if background:
        pid = spawn_worker(cwd, job["id"])
        job["pid"] = pid
        job["status"] = "queued"
        save_job(cwd, job)
        payload = {
            "jobId": job["id"],
            "status": "queued",
            "title": job["title"],
            "summary": job["summary"],
            "logFile": job["logFile"],
            "pid": pid,
        }
        if as_json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"{job['title']} started in the background as {job['id']}. "
                f"Check status with: python3 {Path(__file__).name} status {job['id']}"
            )
        return 0
    return output_job(execute_grok(job, cwd), as_json)


def normalize_effort(value: str | None) -> str | None:
    if not value:
        return None
    effort = value.strip().lower()
    if effort not in VALID_EFFORTS:
        raise BridgeError(f'Unsupported reasoning effort "{value}". Use one of: {", ".join(sorted(VALID_EFFORTS))}.')
    return effort


def handle_review(args: argparse.Namespace, *, kind: str) -> int:
    cwd = Path(args.cwd).resolve()
    require_grok()
    git_root(cwd)
    target = resolve_review_target(cwd, base=args.base, scope=args.scope)
    context = collect_review_context(cwd, target)
    focus = " ".join(args.focus).strip() if getattr(args, "focus", None) else ""
    if kind == "review" and focus:
        raise BridgeError("review does not take extra focus text. Use critique for a steerable pass.")
    prompt_name = "critique" if kind == "critique" else "review"
    prompt = render_prompt(prompt_name, target, context, focus)
    request = {
        "prompt": prompt,
        "model": args.model,
        "effort": normalize_effort(args.effort),
        "write": False,
        "agent": "explore",
        "structured": kind == "critique",
        "base": args.base,
        "scope": target["scope"],
    }
    job = create_job(
        cwd,
        kind=kind,
        title="Grok Build Critique" if kind == "critique" else "Grok Build Review",
        summary=target["label"],
        request=request,
    )
    return enqueue_or_run(cwd, job, background=args.background and not args.wait, as_json=args.json)


def latest_resumable_task(cwd: Path) -> dict[str, Any] | None:
    for job in list_jobs(cwd):
        refresh_job(cwd, job)
        if job.get("kind") != "run":
            continue
        if job.get("status") in {"queued", "running"}:
            raise BridgeError(f"Delegate run {job['id']} is still running. Use status before continuing it.")
        if job.get("sessionId"):
            return job
    return None


def handle_run(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    require_grok()
    prompt = " ".join(args.prompt).strip()
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    resume_last = bool(args.resume_last or args.resume)
    if resume_last and args.fresh:
        raise BridgeError("Choose either --resume/--resume-last or --fresh.")
    resume_id = None
    if resume_last:
        candidate = latest_resumable_task(cwd)
        if not candidate:
            raise BridgeError("No previous Grok Build delegate session was found for this repository.")
        resume_id = candidate["sessionId"]
    if not prompt and not resume_id:
        raise BridgeError("Provide a prompt, --prompt-file, or --resume-last.")
    if not prompt and resume_id:
        prompt = DEFAULT_CONTINUE_PROMPT
    write = bool(args.write)
    request = {
        "prompt": prompt,
        "model": args.model,
        "effort": normalize_effort(args.effort),
        "write": write,
        "agent": None,
        "structured": False,
        "resumeSessionId": resume_id,
    }
    job = create_job(
        cwd,
        kind="run",
        title="Grok Build Resume" if resume_id else "Grok Build Delegate",
        summary=prompt[:96],
        request=request,
        write=write,
    )
    return enqueue_or_run(cwd, job, background=args.background and not args.wait, as_json=args.json)


def handle_status(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    if args.job_id:
        job = refresh_job(cwd, load_job(cwd, args.job_id))
        if args.wait:
            deadline = time.time() + max(0, args.timeout_ms / 1000)
            while job.get("status") in {"queued", "running"} and time.time() < deadline:
                time.sleep(max(0.2, args.poll_interval_ms / 1000))
                job = refresh_job(cwd, load_job(cwd, args.job_id))
        if args.json:
            print(json.dumps(job, indent=2, ensure_ascii=False))
        else:
            print(
                f"{job['id']}  {job.get('status')}  {job.get('title')}  "
                f"session={job.get('sessionId') or '-'}  pid={job.get('pid') or '-'}"
            )
        return 0
    jobs = [refresh_job(cwd, job) for job in list_jobs(cwd)]
    if args.json:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))
        return 0
    if not jobs:
        print("No Grok Build skill jobs for this repository.")
        return 0
    for job in jobs[:20]:
        print(
            f"{job['id']}  {job.get('status'):10}  {job.get('title')}  "
            f"{job.get('summary', '')[:60]}"
        )
    return 0


def handle_show(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    jobs = [refresh_job(cwd, job) for job in list_jobs(cwd)]
    job = load_job(cwd, args.job_id) if args.job_id else next(
        (item for item in jobs if item.get("status") not in {"queued", "running"}),
        None,
    )
    if job is None:
        raise BridgeError("No finished job to show.")
    return output_job(refresh_job(cwd, job), args.json, exit_from_status=False)


def terminate_pid(pid: int) -> dict[str, Any]:
    delivered = False
    method = None
    try:
        os.killpg(pid, signal.SIGTERM)
        delivered = True
        method = "SIGTERM"
        time.sleep(0.4)
        try:
            os.killpg(pid, 0)
            os.killpg(pid, signal.SIGKILL)
            method = "SIGTERM+SIGKILL"
        except OSError:
            pass
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
            delivered = True
            method = "SIGTERM-pid"
        except OSError:
            pass
    return {"pid": pid, "delivered": delivered, "method": method}


def handle_stop(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    jobs = [refresh_job(cwd, job) for job in list_jobs(cwd)]
    job = load_job(cwd, args.job_id) if args.job_id else next(
        (item for item in jobs if item.get("status") in {"queued", "running"}),
        None,
    )
    if job is None:
        raise BridgeError("No running job to stop.")
    kill = terminate_pid(job["pid"]) if job.get("pid") else {"delivered": False, "method": None, "pid": None}
    job["status"] = "cancelled"
    job["finishedAt"] = now_iso()
    job["errorMessage"] = "Stopped by user."
    job["pid"] = None
    save_job(cwd, job)
    payload = {"jobId": job["id"], "status": "cancelled", "kill": kill}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Stopped {job['id']} (kill delivered={kill['delivered']}).")
    return 0


def handle_resume_candidate(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    try:
        candidate = latest_resumable_task(cwd)
        available = bool(candidate)
        error = None
    except BridgeError as exc:
        candidate = None
        available = False
        error = str(exc)
    payload = {
        "available": available,
        "error": error,
        "candidate": None
        if candidate is None
        else {
            "id": candidate["id"],
            "status": candidate.get("status"),
            "title": candidate.get("title"),
            "summary": candidate.get("summary"),
            "sessionId": candidate.get("sessionId"),
            "updatedAt": candidate.get("updatedAt"),
        },
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif candidate:
        print(f"Resumable delegate run found: {candidate['id']} ({candidate.get('status')}).")
    else:
        print(error or "No resumable delegate run found for this repository.")
    return 0


def handle_worker(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    job = load_job(cwd, args.job_id)
    execute_grok(job, cwd)
    return 0 if job.get("status") == "completed" else 1


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portable Grok Build bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    add_common(check)

    for name in ("review", "critique"):
        item = sub.add_parser(name)
        add_common(item)
        item.add_argument("--base")
        item.add_argument("--scope", choices=["auto", "working-tree", "branch"], default="auto")
        item.add_argument("--model")
        item.add_argument("--effort")
        item.add_argument("--background", action="store_true")
        item.add_argument("--wait", action="store_true")
        item.add_argument("focus", nargs="*")

    run = sub.add_parser("run")
    add_common(run)
    run.add_argument("--model")
    run.add_argument("--effort")
    run.add_argument("--write", action="store_true")
    run.add_argument("--resume-last", action="store_true")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--fresh", action="store_true")
    run.add_argument("--background", action="store_true")
    run.add_argument("--wait", action="store_true")
    run.add_argument("--prompt-file")
    run.add_argument("prompt", nargs="*")

    status = sub.add_parser("status")
    add_common(status)
    status.add_argument("job_id", nargs="?")
    status.add_argument("--wait", action="store_true")
    status.add_argument("--timeout-ms", type=int, default=240000)
    status.add_argument("--poll-interval-ms", type=int, default=2000)

    show = sub.add_parser("show")
    add_common(show)
    show.add_argument("job_id", nargs="?")

    stop = sub.add_parser("stop")
    add_common(stop)
    stop.add_argument("job_id", nargs="?")

    candidate = sub.add_parser("run-resume-candidate")
    add_common(candidate)

    worker = sub.add_parser("_worker")
    worker.add_argument("--cwd", required=True)
    worker.add_argument("--job-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "check": handle_check,
        "review": lambda a: handle_review(a, kind="review"),
        "critique": lambda a: handle_review(a, kind="critique"),
        "run": handle_run,
        "status": handle_status,
        "show": handle_show,
        "stop": handle_stop,
        "run-resume-candidate": handle_resume_candidate,
        "_worker": handle_worker,
    }
    try:
        return handlers[args.command](args)
    except BridgeError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except subprocess.TimeoutExpired:
        sys.stderr.write("Timed out waiting for grok.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

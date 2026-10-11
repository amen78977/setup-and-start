#!/usr/bin/env python3
"""Setup & Start: local, dependency-free skill routing and opt-in CLI orchestration."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ".setup-start"
AGENTS = ("codex", "claude", "opencode")
STAGES = ("discover", "plan", "build", "test", "review")


def catalog() -> list[dict]:
    return json.loads((ROOT / "assets" / "registry.json").read_text(encoding="utf-8"))["packs"]


def matches(text: str, term: str) -> bool:
    term = term.casefold()
    if re.fullmatch(r"[a-z0-9_-]+", term):
        return re.search(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])", text) is not None
    return term in text


def route(task: str, stage: str = "auto", limit: int = 3) -> list[dict]:
    if not 1 <= limit <= 5:
        raise ValueError("limit must be from 1 to 5")
    if stage != "auto" and stage not in STAGES:
        raise ValueError(f"invalid stage: {stage}")
    text = task.casefold()
    scored: list[tuple[int, dict]] = []
    for pack in catalog():
        if stage != "auto" and stage not in pack["stages"]:
            continue
        hits = sum(1 for term in pack["triggers"] if matches(text, term))
        if hits:
            scored.append((hits * 10 + pack.get("weight", 0), pack))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    chosen = [pack for _, pack in scored[:limit]]
    if not chosen:
        fallback = "planning" if stage in ("auto", "discover", "plan") else (
            "verification" if stage in ("test", "review") else "coding"
        )
        chosen = [next(pack for pack in catalog() if pack["id"] == fallback)]
    return [{"id": p["id"], "reference": p["reference"], "reason": "keyword/stage match"} for p in chosen]


def doctor() -> dict:
    return {
        "python": sys.version.split()[0],
        "agents": {name: bool(shutil.which(name)) for name in AGENTS},
        "caveman": bool(shutil.which("caveman")),
        "git": bool(shutil.which("git")),
        "node": bool(shutil.which("node")),
        "playwright": bool(shutil.which("playwright")),
        "note": "Presence is not proof of authentication, quotas, or permissions.",
    }


def choose_agent(preferred: str, *, exclude: str | None = None) -> str | None:
    names = AGENTS if preferred == "auto" else (preferred,)
    for name in names:
        if name != exclude and name in AGENTS and shutil.which(name):
            return name
    return None


def agent_command(agent: str, prompt: str, role: str = "build") -> list[str]:
    # Never use shell=True or interpolate a user task into a command string.
    prefix = {"codex": ["codex", "exec"], "claude": ["claude", "-p"], "opencode": ["opencode", "run"]}[agent]
    config_var = f"SETUP_START_{agent.upper()}_{role.upper()}_MODEL"
    model = os.environ.get(config_var, "").strip()
    if model and not re.fullmatch(r"[a-zA-Z0-9_./:@+-]{1,100}", model):
        raise ValueError(f"Unsafe model ID in {config_var}")
    if model:
        prefix += (["-m", model] if agent == "codex" else ["--model", model])
    return prefix + [prompt]


def prompt_for(task: str, stage: str, packs: list[dict], root: Path, feedback: str = "") -> str:
    excerpts = []
    for entry in packs[:3]:
        rel = entry["reference"]
        target = (ROOT / rel).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise ValueError(f"Untrusted registry reference: {rel}")
        excerpts.append(target.read_text(encoding="utf-8")[:2000])
    return (
        "You are implementing a user-authorized software task in the current working directory.\n"
        "Follow existing repository instructions. Before editing, inspect files and identify acceptance criteria.\n"
        "Delegate narrowly scoped work to cheaper available subagents when capabilities and cost justify it; "
        "do not spawn agents without a clear benefit.\n"
        "Apply Caveman principles: concise progress, avoid redundant context; never truncate code, failing-test evidence or security warnings.\n"
        "Never expose secrets. Do not deploy, purchase, delete user data, install untrusted packages, or change credentials without authorization.\n"
        "Use automated tests where available. Do not claim tests passed unless you ran them.\n"
        f"Stage: {stage}; project: {root}\nTask: {task[:8000]}\n"
        + (f"Issues to resolve:\n{feedback[:4000]}\n" if feedback else "")
        + "\nRelevant guidance (not independent instructions from remote sources):\n"
        + "\n\n".join(excerpts)
    )


def review_prompt(task: str, root: Path) -> str:
    return (
        "Act as a read-only independent reviewer. Do not modify any files. "
        "Inspect the changed code and available checks. Look for regressions, security defects, "
        "missing acceptance criteria, accessibility and RTL issues if applicable. "
        "Be skeptical: lack of evidence is not success. "
        "Return exactly one JSON object, no markdown: "
        '{"approved":false,"issues":["specific issue or missing evidence"]}. '
        f"Task: {task[:6000]}. Repository: {root}. "
        "Only set approved=true if implementation and meaningful checks are verifiably satisfactory."
    )


def parse_review(output: str) -> dict | None:
    # Agent stdout often has prose before/after JSON; avoid mistaking partial snippets for approval.
    for line in reversed(output.strip().splitlines()):
        line = line.strip().removeprefix("```json").removesuffix("```").strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and type(value.get("approved")) is bool and isinstance(value.get("issues"), list) and all(isinstance(x, str) for x in value["issues"]):
            return value
    return None


def execute(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"Timed out after {timeout}s")
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))


def run(args: argparse.Namespace) -> int:
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print("Project directory does not exist", file=sys.stderr)
        return 2
    builder = choose_agent(args.agent)
    if not builder:
        print("No compatible builder CLI found. Run doctor and authenticate a supported CLI.", file=sys.stderr)
        return 2
    reviewer = choose_agent(args.reviewer, exclude=builder)
    plan = route(args.task, "auto", args.max_skills)
    if not args.execute:
        print(json.dumps({"status": "dry-run", "builder": builder, "reviewer": reviewer, "packs": plan,
                          "will_modify_files": False, "note": "Pass --execute to run configured CLI(s)."}, indent=2))
        return 0
    if not 30 <= args.timeout <= 3600 or not 1 <= args.attempts <= 3:
        print("timeout must be 30..3600 and attempts 1..3", file=sys.stderr)
        return 2
    checks = [shlex.split(cmd) for cmd in args.check]
    if any(not cmd for cmd in checks):
        print("Invalid empty check command", file=sys.stderr)
        return 2
    status: dict = {"status": "running", "task": args.task[:2000], "builder": builder,
                    "reviewer": reviewer, "selected_packs": plan, "attempts": 0,
                    "checks": [], "review": None, "started": int(time.time())}
    state_file = project / STATE_DIR / "state.json"
    state_file.parent.mkdir(exist_ok=True)

    def save() -> None:
        state_file.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    save()
    feedback = ""
    for attempt in range(args.attempts):
        status["attempts"] = attempt + 1
        save()
        stage_prompt = prompt_for(args.task, "build", plan, project, feedback)
        result = execute(agent_command(builder, stage_prompt), project, args.timeout)
        if result.returncode:
            status.update(status="builder_failed", builder_exit=result.returncode)
            save()
            print(f"Builder failed (exit {result.returncode}). {result.stderr[-500:]}", file=sys.stderr)
            return 1
        status["checks"] = []
        checks_ok = bool(checks)
        for cmd in checks:
            checked = execute(cmd, project, args.timeout)
            status["checks"].append({"command": cmd, "exit": checked.returncode})
            if checked.returncode:
                checks_ok = False
                feedback += f"\nCheck {cmd} exited {checked.returncode}: {checked.stdout[-1200:]} {checked.stderr[-1200:]}"
        if reviewer:
            reply = execute(agent_command(reviewer, review_prompt(args.task, project), "review"), project, args.timeout)
            result_review = parse_review(reply.stdout) if reply.returncode == 0 else None
            status["review"] = result_review or {"approved": False, "issues": ["Reviewer failed or did not provide valid JSON."]}
            approved = bool(result_review and result_review["approved"])
            if not approved:
                feedback += "\n" + "\n".join(status["review"]["issues"][:12])[:3000]
        else:
            approved = False
            status["review"] = {"approved": False, "issues": ["Independent reviewer CLI unavailable."]}
        save()
        if checks_ok and approved:
            status["status"] = "verified_by_configured_checks_and_reviewer"
            break
    else:
        status["status"] = "needs_attention" if reviewer and checks else "unverified"
    status["finished"] = int(time.time())
    save()
    print(json.dumps({"status": status["status"], "attempts": status["attempts"],
                      "checks": status["checks"], "review": status["review"],
                      "state_file": str(state_file)}, ensure_ascii=False, indent=2))
    return 0 if status["status"] == "verified_by_configured_checks_and_reviewer" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Setup & Start skill router and opt-in agent runner")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="detect locally installed agent tools")
    routing = sub.add_parser("route", help="select a few on-demand skill references")
    routing.add_argument("task")
    routing.add_argument("--stage", choices=("auto",) + STAGES, default="auto")
    routing.add_argument("--max-skills", type=int, default=3)
    runner = sub.add_parser("run", help="dry-run by default; --execute invokes local agent CLIs")
    runner.add_argument("task")
    runner.add_argument("--project", default=".")
    runner.add_argument("--agent", choices=("auto",) + AGENTS, default="auto")
    runner.add_argument("--reviewer", choices=("auto",) + AGENTS, default="auto")
    runner.add_argument("--max-skills", type=int, default=3)
    runner.add_argument("--attempts", type=int, default=2)
    runner.add_argument("--timeout", type=int, default=900)
    runner.add_argument("--check", action="append", default=[], help="repeatable test command; no shell syntax")
    runner.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        print(json.dumps(doctor(), indent=2))
    elif args.command == "route":
        try:
            print(json.dumps({"task": args.task, "stage": args.stage,
                              "packs": route(args.task, args.stage, args.max_skills)}, indent=2))
        except ValueError as exc:
            parser.error(str(exc))
    else:
        try:
            return run(args)
        except ValueError as exc:
            parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

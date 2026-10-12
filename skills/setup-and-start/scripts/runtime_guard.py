"""Local execution guard and evidence-only usage accounting.

Does not inspect API keys, call providers to estimate prices, or claim exact
provider spending when token data was not returned by an existing CLI.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid


@contextmanager
def exclusive_run(folder: Path, task_hash: str):
    """Fail closed if an invocation is already editing the same project.

    A stale file requires deliberate manual cleanup after checking processes.
    No PID-based automatic deletion or unbounded lock waits.
    """
    # A pre-existing symlink could otherwise send lock/state outside project.
    parent = folder.parent.resolve()
    if folder.is_symlink():
        raise RuntimeError("Refusing symlinked state directory")
    folder.mkdir(mode=0o700, exist_ok=True)
    if folder.is_symlink() or not folder.resolve().is_relative_to(parent):
        raise RuntimeError("State directory escaped project")
    lock = folder / "run.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(f"Another run may be active ({lock}); verify before removing the lock.") from exc
    try:
        owner = uuid.uuid4().hex
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "started": int(time.time()),
                       "task_hash": task_hash, "owner": owner}, stream)
        yield
    finally:
        try:
            # Do not erase a successor lock that may have replaced ours.
            data = json.loads(lock.read_text(encoding="utf-8"))
            if data.get("owner") == owner:
                lock.unlink()
        except (FileNotFoundError, ValueError, OSError):
            pass


def state_directory(project: Path) -> Path:
    root = project.resolve()
    state = root / ".setup-start"
    if state.is_symlink() or (state.exists() and not state.is_dir()):
        raise ValueError("Unsafe .setup-start state directory")
    state.mkdir(mode=0o700, exist_ok=True)
    if state.is_symlink() or not state.resolve().is_relative_to(root):
        raise ValueError("State directory points outside project")
    return state


def atomic_json_state(state_file: Path, value: dict) -> None:
    """Use unpredictable exclusive temporary name; do not follow state symlinks."""
    if state_file.is_symlink():
        raise ValueError("Unsafe symlinked state file")
    folder = state_file.parent
    if folder.is_symlink():
        raise ValueError("Unsafe symlinked state directory")
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder,
                                         prefix=".state-", suffix=".tmp",
                                         delete=False) as file:
            temp_name = Path(file.name)
            json.dump(value, file, indent=2, ensure_ascii=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        temp_name.replace(state_file)
    finally:
        if temp_name is not None:
            temp_name.unlink(missing_ok=True)


def _usage_from_mapping(value: dict) -> dict | None:
    """Recognize Claude/OpenCode style usage and Codex JSON event usage."""
    usage = value.get("usage", {})
    if not isinstance(usage, dict):
        usage = {}
    # Codex events may provide usage at nested info.total_token_usage.
    nested = value.get("info", {})
    if isinstance(nested, dict):
        if isinstance(nested.get("total_token_usage"), dict):
            usage = nested["total_token_usage"]
    if not usage:
        return None
    inp = usage.get("input_tokens")
    out = usage.get("output_tokens")
    if inp is None:
        inp = usage.get("input")
    if out is None:
        out = usage.get("output")
    if not all(type(x) is int and 0 <= x < 10**9 for x in (inp, out)):
        return None
    return {"input_tokens": inp, "output_tokens": out,
            "total_tokens": inp + out}


def usage_from_output(output: str) -> dict | None:
    """Extract final usage counters from JSON/JSONL; never guess from text size."""
    entries = []
    turns = []
    steps = {}
    cumulative = None
    for line in output.splitlines():
        line = line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            item = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(item, dict):
            continue
        direct = _usage_from_mapping(item)
        if direct:
            entries.append(direct)
            if item.get("type") == "turn.completed":
                turns.append(direct)
            info = item.get("info")
            if isinstance(info, dict) and isinstance(info.get("total_token_usage"), dict):
                cumulative = direct
        # Codex token_count events: .type == turn.completed, .usage;
        # event usage can also be nested in .data.
        data = item.get("data")
        if isinstance(data, dict):
            found = _usage_from_mapping(data)
            if found:
                entries.append(found)
        result = item.get("result")
        if isinstance(result, dict):
            found = _usage_from_mapping(result)
            if found:
                entries.append(found)
        part = item.get("part")
        if isinstance(part, dict) and isinstance(part.get("tokens"), dict):
            tokens = part["tokens"]
            ins, outs = tokens.get("input"), tokens.get("output")
            if type(ins) is int and type(outs) is int and 0 <= ins < 10**9 and 0 <= outs < 10**9:
                counter = {"input_tokens": ins, "output_tokens": outs,
                           "total_tokens": ins + outs}
                entries.append(counter)
                if item.get("type") == "step_finish":
                    steps[part.get("id", len(steps))] = counter
    # Explicit cumulative counters supersede individual turns. Codex turns
    # and OpenCode completed steps are independent counters, not rolling totals.
    if cumulative is not None:
        return cumulative
    independent = turns or list(steps.values())
    if independent:
        return {key: sum(row[key] for row in independent)
                for key in ("input_tokens", "output_tokens", "total_tokens")}
    return entries[-1] if entries else None


def prompt_estimate(chars: int) -> dict:
    """Only a rough context-size *indicator*, not reported provider tokens."""
    return {"prompt_characters": chars, "approx_token_range": [max(1, chars // 6),
              max(1, (chars + 2) // 3)], "measured": False}


def append_telemetry(status: dict, role: str, prompt: str, output: str,
                     elapsed: float, model: str | None, agent: str) -> None:
    record = {"role": role, "agent": agent, "model": model,
              "prompt": prompt_estimate(len(prompt)),
              "seconds": round(elapsed, 3),
              "observed_usage": usage_from_output(output)}
    status.setdefault("telemetry", []).append(record)


def summarize_usage(status: dict) -> dict:
    records = status.get("telemetry", [])
    observed = [x["observed_usage"] for x in records if x.get("observed_usage")]
    return {"invocations": len(records), "usage_reports": len(observed),
            "observed_input_tokens": sum(x["input_tokens"] for x in observed),
            "observed_output_tokens": sum(x["output_tokens"] for x in observed),
            "complete": len(observed) == len(records) and bool(records),
            "warning": "If complete=false, totals are partial; do not compare to full-run token use."}

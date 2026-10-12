"""User-configured, cost-aware model selection, without invented providers or rates."""
from __future__ import annotations

import json
from pathlib import Path
import re

AGENTS = ("codex", "claude", "opencode")
ROLES = ("discover", "plan", "build", "review")
MODES = ("economy", "balanced", "quality")
SAFE_ID = re.compile(r"^[a-zA-Z0-9_./:@+\-]{1,100}$")


def load_policy(path: Path) -> list[dict]:
    data = json.loads(path.expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        raise ValueError("Expected JSON object with models array")
    entries = data["models"]
    if not entries:
        raise ValueError("Model policy has no models; refusing implicit default-provider fallback")
    if len(entries) > 100:
        raise ValueError("Limit model inventory to 100 entries")
    for row in entries:
        if not isinstance(row, dict) or row.get("agent") not in AGENTS:
            raise ValueError("Invalid model agent")
        if not isinstance(row.get("name"), str) or not SAFE_ID.fullmatch(row["name"]):
            raise ValueError("Invalid model identifier")
        if type(row.get("strength")) is not int or not 1 <= row["strength"] <= 5:
            raise ValueError("Model strength must be integer 1..5")
        if any(x not in ROLES for x in row.get("roles", ["build", "review"])):
            raise ValueError("Unrecognized role")
        for k in ("input_per_million", "output_per_million"):
            v = row.get(k)
            if v is not None and (type(v) not in (int, float) or not 0 <= v <= 10000):
                raise ValueError("Invalid model price; use USD per million tokens")
        if type(row.get("available", True)) is not bool:
            raise ValueError("available must be boolean")
        provider = row.get("provider")
        if provider is not None and (not isinstance(provider, str) or not SAFE_ID.fullmatch(provider)):
            raise ValueError("Invalid optional provider identity")
    return entries


def complexity(task: str, role: str) -> int:
    """Heuristic minimum strength, NOT measured model competence."""
    text = task.casefold()
    if role == "discover":
        # Delegated discovery is deliberately a tiny, bounded task: naming
        # likely files and acceptance checks, not solving architecture.
        return 1
    if role == "review":
        base = 3
    elif role == "discover":
        base = 1
    elif role == "plan":
        base = 2
    else:
        base = 2
    high = ("security", "architecture", "migration", "payment", "production",
            "distributed", "auth", "database", "performance", "critical",
            "authentication", "authorization",
            "أمان", "معمارية", "ترحيل", "قاعدة البيانات", "مدفوعات")
    medium = ("integrate", "refactor", "complex", "backend", "api",
              "frontend", "تصميم", "تطوير", "إصلاح")
    def mentioned(term: str) -> bool:
        if term.isascii():
            return re.search(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])", text) is not None
        return term in text

    if any(mentioned(s) for s in high):
        base = max(base, 4)
    elif any(mentioned(s) for s in medium):
        base = max(base, 3)
    if len(text) > 700:
        base = max(base, 3)
    return base


def estimate_cost(row: dict, input_tokens: int = 10000, output_tokens: int = 3000) -> float | None:
    a, b = row.get("input_per_million"), row.get("output_per_million")
    if a is None or b is None:
        return None
    return round((a * input_tokens + b * output_tokens) / 1_000_000, 6)


def repair_candidates(models: list[dict], current: dict, reviewer: dict | None,
                      task: str, mode: str) -> list[dict]:
    """A bounded same-CLI escalation ladder; never reuse the reviewer model."""
    eligible = [row for row in models if row["agent"] == current["agent"]
                and row["strength"] > current["strength"]
                and (reviewer is None or (row["agent"], row["name"]) !=
                     (reviewer["agent"], reviewer["model"]))]
    result = []
    # One preferred model per strength level. Only strict upgrades qualify.
    for strength in sorted({row["strength"] for row in eligible}):
        choice = recommend([row for row in eligible if row["strength"] == strength],
                           task, "build", mode)
        if choice:
            result.append(choice)
    return result


def recommend(models: list[dict], task: str, role: str, mode: str = "balanced",
              agent: str | None = None, exclude: str | None = None,
              exclude_model: tuple[str, str] | None = None) -> dict | None:
    if mode not in MODES or role not in ROLES:
        raise ValueError("Invalid mode or role")
    candidates = []
    requested = complexity(task, role) + (1 if mode == "quality" else 0)
    for row in models:
        if row.get("available", True) is False or row["agent"] == exclude:
            continue
        if exclude_model == (row["agent"], row["name"]):
            continue
        if agent and row["agent"] != agent:
            continue
        if role not in row.get("roles", ["build", "review"]):
            continue
        if row["strength"] < requested:
            continue
        cost = estimate_cost(row)
        # Missing prices cannot be treated as free. Prefer measured pricing.
        price = cost if cost is not None else float("inf")
        if mode == "quality":
            key = (-row["strength"], price, row["agent"], row["name"])
        elif mode == "economy":
            key = (price, row["strength"], row["agent"], row["name"])
        else:
            # Strength remains a user-declared heuristic. Balanced pays a
            # modest premium for stronger qualified models, unlike economy.
            key = (price / row["strength"], -row["strength"], price,
                   row["agent"], row["name"])
        candidates.append((key, row, cost))
    if not candidates:
        return None
    _, row, cost = min(candidates, key=lambda c: c[0])
    return {"agent": row["agent"], "model": row["name"], "strength": row["strength"],
            "provider": row.get("provider"),
            "estimated_usd": cost, "minimum_strength": requested,
            "note": "User-provided rates and strength scores; estimates are not live pricing or benchmarks."}

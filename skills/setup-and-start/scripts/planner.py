"""Deterministic, bounded project discovery and phase-aware skill planning.

No network, dependency installation, repository-wide crawling, or source upload.
Only filenames of known manifests are inspected. This is deliberately a small
router, not an LLM making opaque decisions about what instructions to load.
"""
from __future__ import annotations

import json
from itertools import islice
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("discover", "plan", "build", "test", "review")
MANIFESTS = {
    "package.json": {"frontend", "backend", "coding"},
    "next.config.js": {"frontend"},
    "next.config.mjs": {"frontend"},
    "next.config.ts": {"frontend"},
    "vite.config.ts": {"frontend"},
    "angular.json": {"frontend"},
    "tsconfig.json": {"coding"},
    "pyproject.toml": {"backend", "coding"},
    "requirements.txt": {"backend"},
    "Cargo.toml": {"coding", "desktop"},
    "pubspec.yaml": {"mobile"},
    "app.json": {"mobile"},
    "electron-builder.yml": {"desktop"},
    "tauri.conf.json": {"desktop"},
    "composer.json": {"wordpress", "backend"},
    "wp-config.php": {"wordpress"},
    "Dockerfile": {"deployment"},
    "docker-compose.yml": {"deployment"},
    "compose.yaml": {"deployment"},
}
FILE_HINTS = {
    "src-tauri": "desktop", "electron": "desktop", "android": "mobile",
    "ios": "mobile", "wp-content": "wordpress", "pages": "frontend",
    "app": "frontend", "prisma": "backend", "migrations": "backend",
}
SEPARATORS = re.compile(r"[\s\W_]+", re.UNICODE)
STAGE_DEFAULTS = {"discover": "planning", "plan": "planning",
                  "build": "coding", "test": "verification", "review": "verification"}


def registry() -> list[dict]:
    path = ROOT / "assets" / "registry.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    seen: set[str] = set()
    for pack in doc["packs"]:
        name, ref = pack["id"], pack["reference"]
        if name in seen or not re.fullmatch(r"[a-z0-9-]+", name):
            raise ValueError("Invalid or duplicate registry pack")
        seen.add(name)
        target = (ROOT / ref).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise ValueError("Registry references may only load bundled files: " + ref)
        if not set(pack["stages"]).issubset(STAGES):
            raise ValueError("Invalid pack stages for " + name)
    return doc["packs"]


def project_signals(project: Path | None) -> dict:
    """Read only one directory level of *names*. Do not follow project symlinks."""
    if project is None:
        return {"detected": [], "manifest_names": []}
    base = project.expanduser().resolve()
    if not base.is_dir():
        raise ValueError("Project directory does not exist")
    manifest_names: list[str] = []
    tags: set[str] = set()
    # It is important not to recurse: repositories may be huge or sensitive.
    for p in islice(base.iterdir(), 400):
        if p.is_symlink():
            continue
        if p.is_file() and p.name in MANIFESTS:
            manifest_names.append(p.name)
            tags.update(MANIFESTS[p.name])
        elif p.is_dir() and p.name.lower() in FILE_HINTS:
            tags.add(FILE_HINTS[p.name.lower()])
    return {"detected": sorted(tags), "manifest_names": sorted(manifest_names)}


def matched_terms(text: str, terms: list[str]) -> list[str]:
    text = text.casefold()
    words = set(SEPARATORS.split(text))
    hits = []
    for raw in terms:
        term = raw.casefold()
        if not term:
            continue
        # Don't match "ui" in "build" or "api" inside "capital".
        if re.fullmatch(r"[a-z0-9_-]+", term):
            match = term in words
        else:
            match = term in text
        if match:
            # A user explicitly excluding a technology must not route to its
            # specialist pack just because the excluded word is present.
            if re.search(r"(?:without|except|exclude|بدون|باستثناء)\s+(?:\S+\s+){0,2}"
                         + re.escape(term) + r"(?![a-z0-9_-])", text):
                continue
            hits.append(raw)
    return hits


def select(task: str, stage: str = "auto", limit: int = 3, project: Path | None = None) -> list[dict]:
    if stage != "auto" and stage not in STAGES:
        raise ValueError("Unknown stage: " + stage)
    if not 1 <= limit <= 5:
        raise ValueError("limit must be 1..5")
    signals = project_signals(project)
    all_packs = registry()
    scores: list[tuple[int, dict, list[str]]] = []
    for pack in all_packs:
        if stage != "auto" and stage not in pack["stages"]:
            continue
        hits = matched_terms(task, pack["triggers"])
        if not hits:
            continue
        score = min(4, len(hits)) * 10 + int(pack.get("weight", 0))
        if pack["id"] in signals["detected"]:
            score += 2  # Weak tie-break only: task intent beats repo type.
        scores.append((score, pack, hits))
    scores.sort(key=lambda row: (-row[0], row[1]["id"]))
    chosen = scores[:limit]
    # Risk gates follow the operation, even when the user never says security.
    risky = matched_terms(task, ["auth", "authentication", "authorization", "oauth",
                                "payment", "payments", "permissions", "مصادقة",
                                "صلاحيات", "مدفوعات", "دفع"])
    if risky and stage in ("plan", "test", "review"):
        security = next(p for p in all_packs if p["id"] == "security")
        if not any(p["id"] == "security" for _, p, _ in chosen):
            chosen = [(100, security, risky)] + chosen[:max(0, limit - 1)]
    # Verification is an invariant, not something the user must remember to
    # request explicitly. Reserve one slot in test/review stages for it.
    if stage in ("test", "review") and not any(p["id"] == "verification" for _, p, _ in chosen):
        verification = next(p for p in all_packs if p["id"] == "verification")
        chosen = chosen[:max(0, limit - 1)] + [(0, verification, [])]
    if not chosen:
        fallback = "planning" if stage == "auto" else STAGE_DEFAULTS[stage]
        pack = next(p for p in all_packs if p["id"] == fallback)
        chosen = [(0, pack, [])]
    return [
        {"id": pack["id"], "reference": pack["reference"],
         "reason": ("matched: " + ", ".join(hits[:4])) if hits else "mandatory gate / phase fallback",
         "score": score}
        for score, pack, hits in chosen
    ]


def make_plan(task: str, project: Path | None = None, limit: int = 3) -> dict:
    signals = project_signals(project)
    phases = []
    for stage in STAGES:
        packs = select(task, stage, limit, project)
        # The runner executes one stage at a time. This is a transparent plan
        # of intended guidance, not evidence that work was already done.
        phases.append({"stage": stage, "packs": [p["id"] for p in packs],
                       "references": [p["reference"] for p in packs]})
    ui = any("frontend" in phase["packs"] for phase in phases)
    gates = [
        {"id": "functional", "required": True,
         "evidence": "Existing tests plus a representative user acceptance check; zero tests is failure."},
        {"id": "review", "required": True,
         "evidence": "Fresh reviewer, complete changed source, and resolved findings; unavailable is reported."},
    ]
    if ui:
        gates.append({"id": "ui", "required": True,
                      "evidence": "Mobile/desktop screenshots inspected, keyboard journey, loading/error/empty states, RTL when requested."})
    if any("security" in phase["packs"] for phase in phases):
        gates.append({"id": "security", "required": True,
                      "evidence": "Threat boundaries, negative authorization cases, input validation and sensitive-data handling reviewed."})
    return {"task": task, "project": str(project.resolve()) if project else None,
            "signals": signals, "phases": phases, "max_loaded_per_phase": limit,
            "acceptance_gates": gates,
            "delegation_policy": {
                "default": "Use available native agents for independent bounded tasks when benefit exceeds overhead.",
                "ownership": "One writer per file; delegate read-only discovery/review first.",
                "fallback": "Work inline when agent capability or pricing is unavailable.",
                "integration": "Verify every delegated result before accepting it.",
            },
            "quality_gates": ["actual tests", "independent diff review when available",
                              "responsive and accessibility checks for UI",
                              "explicit evidence and remaining risks"]}


def read_guidance(selected: list[dict], max_chars: int = 4800) -> str:
    """A hard, measurable cap on optional skill instructions per invocation."""
    if not 256 <= max_chars <= 16000:
        raise ValueError("context budget must be 256..16000 characters")
    chunks = []
    remaining = max_chars
    # Mandatory verification must survive a large specialist reference.
    ordered = sorted(selected, key=lambda entry: entry["id"] != "verification")
    for entry in ordered:
        rel = entry["reference"]
        target = (ROOT / rel).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise ValueError("Untrusted registry reference: " + rel)
        data = target.read_text(encoding="utf-8")
        prefix = f"\n## {entry['id']}\n"
        separator = "\n" if chunks else ""
        allowed = max(0, remaining - len(prefix) - len(separator))
        if not allowed:
            break
        # Never silently truncate guidance. If it won't fit, skip and disclose.
        if len(data) > allowed:
            notice = prefix + "[not loaded: exceeds remaining context budget]"
            if len(notice) + len(separator) <= remaining:
                chunks.append(notice)
                remaining -= len(notice) + len(separator)
            continue
        chunks.append(prefix + data)
        remaining -= len(prefix) + len(data) + len(separator)
    return "\n".join(chunks)

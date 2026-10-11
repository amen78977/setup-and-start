#!/usr/bin/env python3
"""Offline selector regression benchmark. No provider calls."""
from __future__ import annotations
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "skills" / "setup-and-start" / "scripts"))
import planner

CASES = [
    ("Build backend API and SQL database", "build", "backend", "frontend"),
    ("Design responsive React UI with RTL", "build", "frontend", "backend"),
    ("Create an Electron desktop app", "build", "desktop", "mobile"),
    ("Create a Flutter Android mobile app", "build", "mobile", "desktop"),
    ("Build a WordPress WooCommerce plugin", "build", "wordpress", "mobile"),
    ("Automate an n8n workflow with Telegram", "build", "automation", "desktop"),
    ("Run Playwright browser screenshots", "test", "browser", "backend"),
    ("Audit OAuth security vulnerabilities", "review", "security", "frontend"),
    ("Plan project architecture and requirements", "plan", "planning", "browser"),
    ("Implement bug fix in source code", "build", "coding", "frontend"),
    ("Deploy Docker release to hosting", "build", "deployment", "desktop"),
    ("Create a database migration plan", "plan", "backend", "frontend"),
    ("Design interface without backend", "build", "frontend", "backend"),
    ("Implement auth endpoint on server", "build", "backend", "frontend"),
    ("Test regressions and quality", "test", "verification", "frontend"),
    ("Refactor a PHP WordPress plugin", "build", "wordpress", "mobile"),
    ("Fix visual CSS spacing in React", "build", "frontend", "backend"),
    ("Plan privacy and security threat model", "plan", "security", "frontend"),
    ("Automate MCP agent workflow", "build", "automation", "frontend"),
]


def evaluate() -> dict:
    packs = planner.registry()
    all_chars = sum(len((planner.ROOT / p["reference"]).read_text(encoding="utf-8")) for p in packs)
    results = []
    for task, stage, required, forbidden in CASES:
        selected = planner.select(task, stage, 3)
        ids = {p["id"] for p in selected}
        chunks = planner.read_guidance(selected)
        results.append({"task": task, "phase": stage, "selected": sorted(ids),
                        "pass": required in ids and forbidden not in ids,
                        "chars_loaded": len(chunks)})
    passed = sum(case["pass"] for case in results)
    return {"total": len(results), "passed": passed, "failed": len(results) - passed,
            "all_packs_chars": all_chars,
            "mean_selected_chars": round(sum(x["chars_loaded"] for x in results) / len(results), 1),
            "note": "Offline routing fixtures and character counts, NOT measured LLM tokens, cost or coding quality.",
            "cases": results}


if __name__ == "__main__":
    print(json.dumps(evaluate(), ensure_ascii=True, indent=2))
    raise SystemExit(0 if evaluate()["failed"] == 0 else 1)

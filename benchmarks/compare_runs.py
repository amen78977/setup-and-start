#!/usr/bin/env python3
"""Compare matched real task trials without guessing missing provider usage."""
from __future__ import annotations

import argparse
import json
import math
from statistics import mean


def compare(records: list[dict]) -> dict:
    if not isinstance(records, list) or not records or len(records) > 10000:
        raise ValueError("Expected 1..10000 trial records")
    pairs = {}
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("Trial must be an object")
        row = dict(row)
        if row.get("variant") not in ("baseline", "skill"):
            raise ValueError("variant must be baseline or skill")
        for key in ("task_id", "acceptance_id", "environment_id"):
            if not isinstance(row.get(key), str) or not 1 <= len(row[key]) <= 100:
                raise ValueError("Nonempty bounded " + key + " required")
        if type(row.get("repetition")) is not int or row["repetition"] < 0:
            raise ValueError("Nonnegative integer repetition required")
        if type(row.get("acceptance_passed")) is not bool:
            raise ValueError("Actual acceptance outcome required")
        if type(row.get("human_interventions")) is not int or row["human_interventions"] < 0:
            raise ValueError("Actual human intervention count required")
        for key in ("tokens", "usd", "seconds"):
            value = row.get(key)
            if value is not None and (type(value) not in (int, float) or
                                      not math.isfinite(value) or value < 0):
                raise ValueError("Invalid observed metric: " + key)
        if row.get("tokens") is not None and type(row["tokens"]) is not int:
            raise ValueError("Observed token count must be an integer")
        if type(row.get("usage_complete", False)) is not bool:
            raise ValueError("usage_complete must be boolean")
        if row.get("usage_complete") is not True:
            row["tokens"] = None
        group = pairs.setdefault((row["task_id"], row["repetition"]), {})
        if row["variant"] in group:
            raise ValueError("Duplicate trial variant")
        group[row["variant"]] = row
    for pair in pairs.values():
        if set(pair) != {"baseline", "skill"}:
            raise ValueError("Every trial needs a matched baseline and skill run")
        for key in ("acceptance_id", "environment_id"):
            if pair["baseline"][key] != pair["skill"][key]:
                raise ValueError("Compared trials must share " + key)
    metrics = {}
    for key in ("tokens", "usd", "seconds", "human_interventions"):
        known = [pair for pair in pairs.values() if all(pair[v].get(key) is not None
                                                       for v in ("baseline", "skill"))]
        baseline = mean(pair["baseline"][key] for pair in known) if known else None
        skill = mean(pair["skill"][key] for pair in known) if known else None
        metrics[key] = {"measured_pairs": len(known), "complete": len(known) == len(pairs),
                        "baseline_mean": baseline, "skill_mean": skill,
                        "relative_change": ((skill - baseline) / baseline
                                            if baseline is not None and baseline > 0 else None)}
    rates = {variant: mean(pair[variant]["acceptance_passed"] for pair in pairs.values())
             for variant in ("baseline", "skill")}
    return {"paired_trials": len(pairs), "distinct_tasks": len({key[0] for key in pairs}),
            "acceptance_pass_rate": rates, "metrics": metrics,
            "note": "Descriptive results from supplied observations, not proof of causality. Missing usage is unknown. Use repeated trials and independent acceptance checks."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON array of matched baseline/skill observations")
    args = parser.parse_args()
    try:
        with open(args.input, encoding="utf-8") as stream:
            print(json.dumps(compare(json.load(stream)), indent=2))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

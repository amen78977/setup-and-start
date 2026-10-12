"""Evidence-based check outcomes, failure diagnosis and UI acceptance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


def check_outcome(command: list[str], exit_code: int, output: str) -> dict:
    output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    runner = any(re.search(r"(?:^|[/\\])(?:pytest|unittest)(?:-?\d+(?:\.\d+)*)?(?:\.exe)?$", arg)
                 for arg in command)
    runner = runner or any(re.fullmatch(r"tests?(?::[\w-]+)?", arg) for arg in command)
    runner = runner or bool(re.search(r"Ran\s+\d+\s+tests?\b|no tests ran", output, re.I))
    runner = runner or bool(re.search(r"\b\d+\s+(?:passed|failed|skipped|xfailed|xpassed|passing|pending)\b", output))
    result = {"pass": exit_code == 0, "executed": None, "skipped": None,
              "expected_failures": None, "passed": None,
              "reason": "command completed" if exit_code == 0 else "command failed"}
    if not runner:
        return result
    unittest = re.search(r"Ran\s+(\d+)\s+tests?\b", output)
    if unittest:
        total = int(unittest[1])
        skip = re.search(r"\bskipped=(\d+)", output)
        skipped = int(skip[1]) if skip else 0
        expected = re.search(r"expected failures=(\d+)", output)
        expected_count = int(expected[1]) if expected else 0
        result.update(executed=max(0, total - skipped), skipped=skipped,
                      expected_failures=expected_count,
                      passed=max(0, total - skipped - expected_count) if exit_code == 0 else None)
        if re.search(r"(?m)^FAILED\b", output):
            result.update({"pass": False, "reason": "test runner reported failures"})
    else:
        # Pytest reports passed/failed/skipped/deselected separately.
        counts = {key: sum(int(n) for n in re.findall(r"(\d+)\s+" + key + r"\b", output))
                  for key in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")}
        counts["passed"] += sum(map(int, re.findall(r"(\d+)\s+passing\b", output)))
        counts["skipped"] += sum(map(int, re.findall(r"(\d+)\s+pending\b", output)))
        # Jest lists label after number: Tests: 1 skipped, 2 passed, 3 total.
        if any(counts.values()) or re.search(r"no tests ran|collected\s+0\s+items", output, re.I):
            result.update(executed=counts["passed"] + counts["failed"] + counts["xpassed"] + counts["xfailed"],
                          skipped=counts["skipped"], expected_failures=counts["xfailed"], passed=counts["passed"])
        if counts["failed"] or counts["error"]:
            result.update({"pass": False, "reason": "test runner reported failures"})
    if result["executed"] is None:
        result.update({"pass": False, "reason": "test execution counts unavailable"})
    elif result["executed"] == 0:
        result.update({"pass": False, "reason": "no non-skipped tests executed"})
    elif result["passed"] == 0:
        result.update({"pass": False, "reason": "no successful tests demonstrated"})
    return result


def diagnose(exit_code: int, output: str, phase: str = "build") -> dict:
    text = output.casefold()
    if exit_code == 124:
        return {"kind": "timeout", "escalate": False, "retry": False}
    if exit_code == 127 or any(term in text for term in (
            "command not found", "modulenotfounderror", "no module named")):
        return {"kind": "environment", "escalate": False, "retry": False}
    # Assertions about 401/403, connection failures or quotas are test results,
    # not evidence that the runner's own provider authentication failed.
    if (phase == "check" and re.search(r"\bassertion\b|\bexpected\b", text)) or re.search(
            r"\bassertionerror\b|\bassert\s+|\bexpected\b.*\b(?:received|got|actual)\b", text):
        return {"kind": "implementation", "escalate": True, "retry": True}
    if any(term in text for term in (
            "connection refused", "could not resolve host", "certificate verify failed")):
        return {"kind": "environment", "escalate": False, "retry": False}
    if any(term in text for term in ("unauthorized", "authentication failed", "quota exceeded",
                                    "rate limit", "insufficient credits", "permission denied")):
        return {"kind": "access", "escalate": False, "retry": False}
    return {"kind": "implementation", "escalate": True, "retry": True}


def ui_acceptance(path: Path | None, screenshots: Path, source_sha: str | None) -> dict:
    """Validate explicit inspection evidence against this run's actual outputs.

    This authenticates artifact identity, not the honesty of the inspecting agent.
    Automated capture alone never substitutes for visual/journey inspection.
    """
    if path is None:
        return {"pass": False, "reason": "UI inspection evidence missing"}
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16000:
            raise ValueError("invalid UI evidence file")
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or not source_sha or doc.get("source_sha256") != source_sha:
            raise ValueError("UI evidence does not match current source")
        reviewer = doc.get("reviewer")
        if not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 100:
            raise ValueError("UI inspector identity missing")
        journeys = doc.get("checks", {})
        required = ("visual", "keyboard", "responsive", "states")
        if not isinstance(journeys, dict) or any(
                not isinstance(journeys.get(key), str) or not 10 <= len(journeys[key].strip()) <= 500
                for key in required):
            raise ValueError("concrete visual, keyboard, responsive and state evidence required")
        if doc.get("approved") is not True or doc.get("issues") != []:
            raise ValueError("UI issues remain unresolved")
        digests = doc.get("screenshots", {})
        for viewport in ("mobile", "desktop"):
            target = screenshots / (viewport + ".png")
            if target.is_symlink() or not target.is_file():
                raise ValueError("current screenshots missing")
            if target.stat().st_size > 20_000_000:
                raise ValueError("screenshot exceeds size limit")
            if not isinstance(digests, dict) or digests.get(viewport) != hashlib.sha256(target.read_bytes()).hexdigest():
                raise ValueError("UI evidence does not match current screenshots")
        return {"pass": True, "reason": "artifact-bound UI inspection supplied", "reviewer": reviewer}
    except (OSError, ValueError, TypeError) as exc:
        return {"pass": False, "reason": str(exc)}

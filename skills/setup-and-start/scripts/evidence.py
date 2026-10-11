"""Bounded local evidence for a second reviewer.

Reviewer runs in a temporary cwd and receives curated evidence, NOT a path to
the full working repository. A cwd is not a security sandbox; an external CLI
may still have filesystem/network access. Use a trusted provider/runtime.
"""
from __future__ import annotations

import hashlib
from itertools import islice
from pathlib import Path
import re
import subprocess

ALLOWED_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
                    ".php", ".css", ".html", ".md", ".json", ".yml", ".yaml", ".toml"}
DENY_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
SENSITIVE = re.compile(r"(?i)(api[_-]?key|password|secret|authorization|private[_-]?key|token)\s*[:=]\s*['\"]?[^\s'\"]{6,}")
SOURCE_FOLDERS = ("src", "app", "lib", "pages", "tests")


def _git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(project), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          check=False, timeout=15)


def _safe_name(relative: str) -> bool:
    p = Path(relative.replace("\\", "/"))
    return (not p.is_absolute() and ".." not in p.parts
            and p.name not in DENY_NAMES
            and not any(x.startswith(".env") for x in p.parts)
            and ".setup-start" not in p.parts and ".git" not in p.parts
            and p.suffix.lower() in ALLOWED_SUFFIXES)


def _source_snapshot(project: Path, max_bytes: int) -> dict:
    """Non-Git starter projects can still receive bounded source review."""
    candidates = list(islice(project.iterdir(), 100))
    for folder in SOURCE_FOLDERS:
        source = project / folder
        if source.is_dir() and not source.is_symlink():
            candidates.extend(islice(source.rglob("*"), 100))
    texts = []
    filenames = []
    used = 0
    for target in candidates:
        if target.is_symlink() or not target.is_file():
            continue
        rel = target.relative_to(project).as_posix()
        if not _safe_name(rel):
            continue
        if target.stat().st_size > 10000:
            return {"available": False, "reason": "Source file too large for bounded review",
                    "changed": [], "patch": ""}
        body = target.read_text(encoding="utf-8", errors="replace")
        if SENSITIVE.search(body):
            return {"available": False, "reason": "Potential credential in source snapshot",
                    "changed": [], "patch": ""}
        excerpt = f"\n--- SOURCE FILE: {rel} ---\n{body}\n"
        used += len(excerpt.encode("utf-8"))
        if used > max_bytes:
            return {"available": False, "reason": "Source snapshot exceeds evidence budget",
                    "changed": [], "patch": ""}
        texts.append(excerpt)
        filenames.append(rel)
    patch = "".join(texts)
    return {"available": bool(texts), "reason": "Non-Git source snapshot" if texts else "No reviewable source files",
            "changed": filenames, "patch": patch,
            "sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest()}


def collect(project: Path, max_bytes: int = 40000) -> dict:
    """Collect changed tracked diff and selected untracked source safely."""
    if not 1024 <= max_bytes <= 150000:
        raise ValueError("Evidence budget must be 1024..150000 bytes")
    inside = _git(project, "rev-parse", "--is-inside-work-tree")
    if inside.returncode or inside.stdout.strip() != "true":
        return _source_snapshot(project, max_bytes)
    status = _git(project, "status", "--porcelain", "--untracked-files=normal")
    if status.returncode:
        return {"available": False, "reason": "git status failed", "changed": [], "patch": ""}
    # Track selected paths only: no build caches, .env, binary or git config.
    filenames = []
    for line in status.stdout.splitlines():
        name = line[3:].strip()
        if " -> " in name:
            name = name.split(" -> ")[-1]
        if _safe_name(name):
            filenames.append(name)
    filenames = sorted(set(filenames))[:100]
    if not filenames:
        return {"available": False, "reason": "No reviewable changed source files",
                "changed": [], "patch": ""}
    tracked = [p for p in filenames if _git(project, "ls-files", "--error-unmatch", "--", p).returncode == 0]
    chunks = []
    if tracked:
        diff = _git(project, "diff", "--no-ext-diff", "HEAD", "--", *tracked)
        if diff.returncode:
            return {"available": False, "reason": "git diff failed", "changed": filenames, "patch": ""}
        chunks.append(diff.stdout)
    # git diff HEAD does not include new untracked files; include limited source previews.
    for name in filenames:
        if name in tracked:
            continue
        target = (project / name).resolve()
        if not target.is_relative_to(project.resolve()) or not target.is_file():
            continue
        if target.stat().st_size > 12000:
            chunks.append("\n[omitted oversized untracked file: " + name + "]")
            continue
        chunks.append("\n--- NEW FILE " + name + " ---\n"
                      + target.read_text(encoding="utf-8", errors="replace"))
    patch = "\n".join(chunks)
    # Do not send secret-looking values to a second provider by default.
    has_secrets = bool(SENSITIVE.search(patch))
    if has_secrets:
        return {"available": False, "reason": "Potential credential in diff; review locally",
                "changed": filenames, "patch": ""}
    encoded = patch.encode("utf-8")
    if len(encoded) > max_bytes:
        return {"available": False, "reason": "Diff exceeds evidence budget",
                "changed": filenames, "patch": ""}
    return {"available": bool(patch.strip()), "reason": "changed-file evidence",
            "changed": filenames, "patch": patch,
            "sha256": hashlib.sha256(encoded).hexdigest()}

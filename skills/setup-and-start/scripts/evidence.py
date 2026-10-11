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
SENSITIVE = re.compile(
    r"""(?ix)
      (?:["']?\b(?:api[_-]?key|password|passwd|secret|client[_-]?secret|
        private[_-]?key|access[_-]?token|refresh[_-]?token|authorization|
        cookie|set-cookie)\b["']?\s*[:=]\s*["']?[^\s"',;]{7,})
      |(?:\bBearer\s+[A-Za-z0-9._~+/=-]{12,})
      |(?:-----BEGIN\s+(?:[A-Z]+\s+)?PRIVATE\s+KEY-----)
      |(?:\b(?:ghp_|gho_|ghs_|ghu_|github_pat_|sk-)[A-Za-z0-9_\-]{14,})
      |(?:\bAKIA[0-9A-Z]{16}\b)
    """)
SOURCE_FOLDERS = ("src", "app", "lib", "pages", "tests")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", ".next", "dist", "build",
             "__pycache__", ".setup-start"}
SENSITIVE_NAMES = re.compile(r"(?i)(secret|credential|private[_-]?key|\.env|service[_-]?account|token)")


def _git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    command = ["git", "-C", str(project), *args]
    try:
        return subprocess.run(command, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 127, "", type(exc).__name__)


def _safe_name(relative: str) -> bool:
    p = Path(relative.replace("\\", "/"))
    return (not p.is_absolute() and ".." not in p.parts
            and p.name not in DENY_NAMES
            and not any(x.lower() in SKIP_DIRS for x in p.parts)
            and not any(SENSITIVE_NAMES.search(x) for x in p.parts)
            and ".setup-start" not in p.parts and ".git" not in p.parts
            and p.suffix.lower() in ALLOWED_SUFFIXES)


def _source_snapshot(project: Path, max_bytes: int,
                     baseline_files: dict[str, str] | None = None) -> dict:
    """Non-Git starter projects can still receive bounded source review."""
    candidates = list(islice(project.iterdir(), 100))
    for folder in SOURCE_FOLDERS:
        source = project / folder
        if source.is_dir() and not source.is_symlink():
            # Two levels only: an unbounded rglob may walk private dependencies,
            # huge generated code, or deeply nested symlinks.
            for item in islice(source.iterdir(), 100):
                if item.is_symlink():
                    continue
                candidates.append(item)
                if item.is_dir() and item.name not in SKIP_DIRS:
                    candidates.extend(islice(item.iterdir(), 50))
    texts = []
    filenames = []
    file_hashes = {}
    used = 0
    for target in candidates:
        if target.is_symlink() or not target.is_file():
            continue
        if not target.resolve().is_relative_to(project.resolve()):
            continue
        rel = target.relative_to(project).as_posix()
        if not _safe_name(rel):
            continue
        if target.stat().st_size > 10000:
            return {"available": False, "reason": "Source file too large for bounded review",
                    "changed": [], "patch": ""}
        body = target.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        file_hashes[rel] = digest
        if baseline_files is not None and baseline_files.get(rel) == digest:
            continue
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
            "file_hashes": file_hashes,
            "sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest()}


def collect(project: Path, max_bytes: int = 40000, baseline: str | None = None,
            source_baseline: dict[str, str] | None = None) -> dict:
    """Collect bounded changed source, including builder commits since baseline.

    The baseline must come from git rev-parse HEAD of this same repository.
    Never pass arbitrary git revision expressions supplied by an untrusted task.
    """
    if not 1024 <= max_bytes <= 150000:
        raise ValueError("Evidence budget must be 1024..150000 bytes")
    inside = _git(project, "rev-parse", "--is-inside-work-tree")
    if inside.returncode or inside.stdout.strip() != "true":
        return _source_snapshot(project, max_bytes, source_baseline)
    if baseline is not None:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", baseline):
            raise ValueError("baseline must be a 40-character commit SHA")
        valid = _git(project, "cat-file", "-t", baseline)
        if valid.returncode or valid.stdout.strip() != "commit":
            raise ValueError("baseline commit not present in this repository")
    status = _git(project, "status", "--porcelain", "--untracked-files=all")
    if status.returncode:
        return {"available": False, "reason": "git status failed", "changed": [], "patch": ""}
    # Track selected paths only: no build caches, .env, binary or git config.
    filenames = []
    excluded_sensitive = []
    for line in status.stdout.splitlines():
        name = line[3:].strip()
        if " -> " in name:
            name = name.split(" -> ")[-1]
        if _safe_name(name):
            filenames.append(name)
        elif SENSITIVE_NAMES.search(name) or Path(name).name in DENY_NAMES:
            excluded_sensitive.append(name)
    if baseline is not None:
        committed = _git(project, "diff", "--name-only", "--diff-filter=ACMRD",
                         baseline, "HEAD")
        if committed.returncode:
            return {"available": False, "reason": "Cannot compare baseline with HEAD",
                    "changed": [], "patch": ""}
        for name in committed.stdout.splitlines():
            if _safe_name(name):
                filenames.append(name)
            elif SENSITIVE_NAMES.search(name) or Path(name).name in DENY_NAMES:
                excluded_sensitive.append(name)
    if excluded_sensitive:
        return {"available": False, "reason": "Changes include sensitive filenames; local-only review required",
                "changed": [], "patch": ""}
    filenames = sorted(set(filenames))[:100]
    if not filenames:
        return {"available": False, "reason": "No reviewable changed source files",
                "changed": [], "patch": ""}
    tracked = []
    for name in filenames:
        in_head = _git(project, "ls-files", "--error-unmatch", "--", name).returncode == 0
        in_base = (baseline is not None and
                   bool(_git(project, "ls-tree", "--name-only", "-r", baseline, "--", name).stdout.strip()))
        if in_head or in_base:
            tracked.append(name)
    chunks = []
    if tracked:
        diff = _git(project, "diff", "--no-ext-diff", "--no-textconv",
                    baseline or "HEAD", "--", *tracked)
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

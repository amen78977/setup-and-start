"""Bounded local evidence for a second reviewer.

Reviewer runs in a temporary cwd and receives curated evidence, NOT a path to
the full working repository. A cwd is not a security sandbox; an external CLI
may still have filesystem/network access. Use a trusted provider/runtime.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import subprocess

ALLOWED_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
                    ".php", ".css", ".html", ".md", ".json", ".yml", ".yaml", ".toml",
                    ".vue", ".svelte", ".dart", ".kt", ".swift", ".scss", ".sass",
                    ".sql", ".sh", ".ps1", ".c", ".cpp", ".h", ".hpp", ".cs",
                    ".rb", ".ex", ".exs", ".astro", ".mdx", ".xml", ".gradle"}
TEXT_NAMES = {".gitignore", ".gitattributes", ".dockerignore", "Dockerfile",
              "Makefile", "LICENSE", "Procfile"}
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


def _safe_name(relative: str, allow_cache: bool = False) -> bool:
    p = Path(relative.replace("\\", "/"))
    return (not p.is_absolute() and ".." not in p.parts
            and p.name not in DENY_NAMES
            and (allow_cache or not any(x.lower() in SKIP_DIRS for x in p.parts))
            and not any(SENSITIVE_NAMES.search(x) for x in p.parts)
            and ".setup-start" not in p.parts and ".git" not in p.parts
            and (p.suffix.lower() in ALLOWED_SUFFIXES or p.name in TEXT_NAMES))


def _source_snapshot(project: Path, max_bytes: int,
                     baseline_files: dict[str, str] | None = None) -> dict:
    """Non-Git starter projects can still receive bounded source review."""
    candidates = []
    failures = []
    directory_count = 0
    def scan_error(error):
        failures.append("Cannot enumerate project: " + type(error).__name__)
    # Walk the full source tree with explicit bounds. Crossing a bound is a
    # blocker, never a silent partial snapshot. Do not follow directory links.
    for folder, directories, files in os.walk(project, followlinks=False, onerror=scan_error):
        directory_count += 1
        if directory_count > 2000:
            failures.append("Source traversal exceeds directory budget")
            break
        directories[:] = sorted(name for name in directories if name not in SKIP_DIRS)
        for name in directories:
            if (Path(folder) / name).is_symlink():
                failures.append("Symlinked directory requires local review")
        if len(Path(folder).relative_to(project).parts) > 30:
            failures.append("Source traversal depth exceeded")
            break
        candidates.extend(Path(folder) / name for name in sorted(files))
        if len(candidates) > 2000:
            failures.append("Source traversal exceeds 2000-file budget")
            break
    if failures:
        return {"available": False, "scan_complete": False, "reason": failures[0],
                "changed": [], "patch": ""}
    texts = []
    filenames = []
    file_hashes = {}
    used = 0
    hash_bytes = 0
    for target in candidates:
        if target.is_symlink() or not target.is_file():
            return {"available": False, "scan_complete": False,
                    "reason": "Symlinked or unreadable source requires local review", "changed": [], "patch": ""}
        if not target.resolve().is_relative_to(project.resolve()):
            continue
        rel = target.relative_to(project).as_posix()
        if SENSITIVE_NAMES.search(rel) or target.name in DENY_NAMES:
            return {"available": False, "scan_complete": False,
                    "reason": "Sensitive paths require local review", "changed": [], "patch": ""}
        if target.stat().st_size > 1_000_000:
            return {"available": False, "scan_complete": False, "reason": "Source hashing budget exceeded",
                    "changed": [], "patch": ""}
        hash_bytes += target.stat().st_size
        if hash_bytes > 20_000_000:
            return {"available": False, "scan_complete": False, "reason": "Total source hashing budget exceeded",
                    "changed": [], "patch": ""}
        raw = target.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        file_hashes[rel] = digest
        if baseline_files is not None and baseline_files.get(rel) == digest:
            continue
        if not _safe_name(rel) or len(raw) > 10000:
            return {"available": False, "scan_complete": False,
                    "reason": "Unsupported or oversized source requires local review: " + rel,
                    "changed": [], "patch": ""}
        try:
            body = raw.decode("utf-8")
        except UnicodeDecodeError:
            body = "\0"
        if "\0" in body:
            return {"available": False, "scan_complete": False,
                    "reason": "Non-text source requires local review", "changed": [], "patch": ""}
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
    if baseline_files:
        deleted = sorted(set(baseline_files) - set(file_hashes))
        if deleted:
            # We have hashes of old files but not their contents. Do not allow
            # an external reviewer to overlook removals and approve blindly.
            names = ", ".join(deleted[:12])
            return {"available": False, "reason": "Source file deletion requires local review: " + names,
                    "changed": deleted, "patch": "", "file_hashes": file_hashes}
    patch = "".join(texts)
    return {"available": bool(texts), "scan_complete": True,
            "reason": "Non-Git source snapshot" if texts else "No reviewable source files",
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
    status = _git(project, "status", "--porcelain", "-z", "--untracked-files=all")
    if status.returncode:
        return {"available": False, "reason": "git status failed", "changed": [], "patch": ""}
    # Track selected paths only: no build caches, .env, binary or git config.
    filenames = []
    excluded_sensitive = []
    unsupported = []

    def classify(name, tracked=False):
        # Git-tracked files are project content regardless of folder naming.
        # Cache exclusions apply only to untracked outputs, never tracked code.
        if _safe_name(name, allow_cache=tracked):
            filenames.append(name)
        elif SENSITIVE_NAMES.search(name) or Path(name).name in DENY_NAMES:
            excluded_sensitive.append(name)
        elif tracked or not any(part in SKIP_DIRS for part in Path(name).parts):
            unsupported.append(name)

    records = iter(status.stdout.split("\0"))
    for line in records:
        if not line:
            continue
        change = line[:2]
        name = line[3:]
        if "R" in change or "C" in change:
            # -z format provides the former name as the next NUL record.
            former = next(records, None)
            if former:
                classify(former, tracked=True)
        classify(name, tracked=change != "??")
    if baseline is not None:
        committed = _git(project, "diff", "--no-renames", "--name-only", "-z", "--diff-filter=ACMRD",
                         baseline, "HEAD")
        if committed.returncode:
            return {"available": False, "reason": "Cannot compare baseline with HEAD",
                    "changed": [], "patch": ""}
        for name in committed.stdout.split("\0"):
            if not name:
                continue
            classify(name, tracked=True)
    if unsupported:
        return {"available": False, "reason": "Unsupported changed paths require local review: " + ", ".join(unsupported[:5]),
                "changed": sorted(set(filenames + unsupported)), "patch": ""}
    if excluded_sensitive:
        return {"available": False, "reason": "Changes include sensitive filenames; local-only review required",
                "changed": [], "patch": ""}
    filenames = sorted(set(filenames))
    if len(filenames) > 100:
        return {"available": False, "reason": "More than 100 changed source paths: partial review prohibited",
                "changed": [], "patch": ""}
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
        if re.search(r"(?m)^(?:Binary files |GIT binary patch)", diff.stdout):
            return {"available": False, "reason": "Binary changes require local review",
                    "changed": filenames, "patch": ""}
        chunks.append(diff.stdout)
    # git diff HEAD does not include new untracked files; include limited source previews.
    for name in filenames:
        if name in tracked:
            continue
        original = project / name
        target = original.resolve()
        if original.is_symlink() or not target.is_relative_to(project.resolve()):
            return {"available": False, "reason": "Symlinked or escaped source requires local review",
                    "changed": filenames, "patch": ""}
        if not target.is_relative_to(project.resolve()) or not target.is_file():
            continue
        if target.stat().st_size > 12000:
            return {"available": False, "reason": "Untracked source file exceeds review budget: " + name,
                    "changed": filenames, "patch": ""}
        raw = target.read_bytes()
        try:
            body = raw.decode("utf-8")
        except UnicodeDecodeError:
            body = None
        if body is None or b"\0" in raw:
            return {"available": False, "reason": "Non-text source requires local review: " + name,
                    "changed": filenames, "patch": ""}
        chunks.append("\n--- NEW FILE " + name + " ---\n"
                      + body)
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

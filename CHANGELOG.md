# Changelog

## v1.0.0 — stable core

- One Agent Skills entrypoint with progressive disclosure, 12 curated phase-aware packs and built-in Caveman-style context discipline.
- Portable routing/CLI runner supporting existing Codex, Claude Code, and OpenCode installations.
- User-owned model-price inventory and bounded optional economy-mode discovery delegation; no imaginary model IDs/prices.
- Configured checks, an independent diff-based review when a second compatible CLI is present, retry bounds, and optional browser screenshots.
- Fail closed for sensitive or unreviewable change evidence, empty test suites, unsafe paths, and concurrent project runs.
- Avoid repeated paid build turns when a reviewer cannot run; status explicitly distinguishes unreviewed from fully verified results.
- Fixed Windows argument parsing for check commands; added actual local subprocess integration tests and browser smoke validation.
- GitHub Actions checks Windows and Linux with Python 3.10, 3.11 and 3.13, plus offline routing fixtures.

This is a stable **core workflow**, not a universal zero-error coding system.
Not provided: model accounts, real billing limits, native parallel subagent teams,
hosted deployment, a sandboxed untrusted-code runner, or a bundled Caveman proxy.

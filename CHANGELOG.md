# Changelog

## v1.1.0 — evidence and adaptive repair (2026-10-12)

- Include Git-tracked source under cache-named directories in dirty and committed evidence; preserve committed deletions and block unsupported tracked assets.
- Distinguish assertions about authentication/connectivity from actual execution blockers, preserving repair escalation for failed authorization tests.
- Recognize versioned pytest executables and wrapped test summaries, strip terminal color codes, and reject failure summaries even when a wrapper returns zero.
- Add nine regression cases reproducing the latest review findings.

- Require successful executed unittest/pytest/test-script cases; record skipped and expected-failure outcomes separately and reject missing execution evidence.
- Replace partial non-Git discovery with bounded complete-tree scanning; overflow, unsupported source and sensitive paths block approval explicitly.
- Diagnose external failures before paid repair; restore model/diagnosis and mark discovery attempted before invocation for reliable resume.
- Enforce UI acceptance with current smoke results and source/screenshot-bound visual/journey inspection; support runtime URL discovery and system Chromium.
- Add optional provider identity, honest review-independence reporting, paired real-trial comparison tooling and dedicated pinned browser CI.

- Automatically escalate repair attempts to stronger configured models on the same CLI; exclude the reviewer model and include all eligible upgrade prices in the forecast envelope. `--no-escalation` disables this behavior.
- Defer reviewer invocations until functional checks pass, avoiding review calls for already-failing builds.
- Reserve security guidance for authentication, authorization and payment work; expose the security acceptance gate in plans.
- Refuse unsupported, binary or symlinked new-file evidence and include common extensionless configuration files in review.

- Refuse partial review when oversized untracked source is omitted.
- Aggregate independent Codex turns and OpenCode steps; preserve cumulative counters and deduplicate identified steps.
- Keep mandatory verification guidance first, account for separators in context limits, and continue loading smaller packs after oversized references.
- Distinguish balanced quality/price selection from minimum-price economy mode.
- Prefer a separate reviewer provider, with a distinct configured model on the same CLI as a fallback.
- Preserve repair diagnostics across resume and replace stale feedback each attempt.
- Add explicit acceptance gates and delegation ownership to phase plans, plus an autonomous decision protocol with UI evidence requirements.
- Add regression and subprocess integration coverage for these paths.

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

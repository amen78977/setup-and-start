# Setup & Start — milestones and definition of done

## v0.1 (this PR)
- [x] Single low-context entry skill, bounded reference router, curated packs.
- [x] Caveman token-discipline instructions, no unreviewed vendoring.
- [x] Native CLI detection and opt-in execution, no shell injection for user prompts.
- [x] User-supplied test commands, separate CLI review, bounded retry and honest status reporting.
- [x] Standard-library regression tests and CI configuration.

## v0.2 — correctness hardening
- [ ] Isolated worktrees or containers for builder/reviewer (reviewer must be truly read-only).
- [ ] Checkpoint-based resumption, job cancellation and idempotent retries.
- [ ] Structured stage outputs and detailed evidence manifest instead of natural-language-only reviews.
- [ ] Robust browser smoke tests / RTL / accessibility through installed Playwright or agent-browser.
- [ ] Explicit user-approved external skill pinning, license review and optional installs.

## v0.3 — model economics
- [ ] Per-provider adapter matrix, actual token accounting, quotas and calibrated model competence.
- [ ] Measured task-based economic router with tool-call overhead, fallback and safety budgets.
- [ ] Browser/UI/desktop/mobile/WordPress integration tests on disposable demo projects.
- [ ] Benchmarks vs plain Claude Code, Codex and OpenCode for pass rate, tokens and human intervention.

## Definition of done for each milestone
- Requirements and threat boundaries documented.
- Automated tests and a real end-to-end use case complete with recorded evidence.
- No secrets, destructive side effects or unstated manual prerequisites.
- Human-reviewed licensing of redistributed third-party assets.

No milestone should claim a universal 0-bug guarantee or measured token reductions without data.

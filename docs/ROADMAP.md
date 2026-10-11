# Setup & Start — milestones and definition of done

## v0.1 — shipped
- [x] Single low-context entry skill, bounded reference router, curated packs.
- [x] Caveman token-discipline instructions, no unreviewed vendoring.
- [x] Native CLI detection and opt-in execution, no shell injection for user prompts.
- [x] User-supplied test commands, separate CLI review, bounded retry and honest status reporting.
- [x] Standard-library regression tests and CI configuration.

## v0.2 — correctness and transparency (shipped)
- [x] Deterministic, phase-specific routing with a strict context-budget, registry validation and lightweight project-type signals.
- [x] Resume attempts from atomic JSON checkpoints (not exactly-once execution).
- [x] Evidence manifest with changed-source diff, strict typed review decision, checks and bounded repair attempts.
- [x] Separate disposable working directory for reviewer and safety screen for probable secrets (NOT an OS sandbox).
- [x] Optional Playwright browser smoke/screenshot capture at desktop/mobile widths, no browser auto-install.
- [x] User-provided model inventory, heuristic role/price router (NOT live model metering).
- [x] Expanded regression tests and CI across Windows/Linux with supported Python versions.
- [ ] True OS-isolated builder/reviewer containers, cancellation and process-tree cleanup.
- [ ] Crash-consistent event journal and exactly-once/idempotent retries.
- [ ] Automatic browser-based UI evaluation inside runner; human/vision screenshot assessment.
- [ ] Explicit user-approved external skill pinning, license review and optional installs.

## v0.3 — model economics (current experimental)
- [x] Explicit opt-in structured-output token accounting for supported CLI schemas; unknowns remain unknown.
- [x] Run lock, baseline-aware committed-diff review, retry on builder failure, optional browser gate.
- [x] Economically conditional small-model discovery delegation using a user-owned priced model inventory.
- [x] Approximate per-run forecast rejection (NOT a billing cap).
- [x] Offline routing benchmark with honest character-load comparisons.
- [ ] Real token accounting for every vendor, model quota visibility, provider adapter matrix and calibrated model competence.
- [ ] Measured task-based economic router with tool-call overhead, fallback and safety budgets.
- [ ] Native per-platform subagent spawning, work ownership and reconciliation; no assumed cross-provider access.
- [ ] Browser/UI/desktop/mobile/WordPress integration tests on disposable demo projects.
- [ ] Benchmarks vs plain Claude Code, Codex and OpenCode for pass rate, tokens and human intervention.

## Definition of done for each milestone
- Requirements and threat boundaries documented.
- Automated tests and a real end-to-end use case complete with recorded evidence.
- No secrets, destructive side effects or unstated manual prerequisites.
- Human-reviewed licensing of redistributed third-party assets.

No milestone should claim a universal 0-bug guarantee or measured token reductions without data.

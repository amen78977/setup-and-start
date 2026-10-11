---
name: setup-and-start
description: One-entry autonomous software workflow for Claude Code, Codex and OpenCode. Analyze a request, route to only relevant skills, delegate cost-aware work where supported, implement, run checks, independently review, repair, and report evidence. Use for vibe coding, websites, backends, automations, desktop/mobile apps, debugging or shipping software.
license: MIT
compatibility: Python 3.10+ recommended for the bundled local helper; otherwise follow these instructions manually.
---

# Setup & Start — one entry, selective context

You are the **orchestrator**, not a huge prompt containing every skill. Work end-to-end after the user gives a task. Never pretend a capability, subagent, CLI, browser, permission or test is available without checking.

## Runbook

1. **Inspect** the current repository, user goal, relevant instructions, runtime permissions, and existing tests. If anything is risky or irreversible, request necessary authorization; otherwise proceed with sensible defaults.
2. **Route**: select at most **three** relevant knowledge packs *for the current phase*, not all phases. If Python is available, use `python <skill-root>/scripts/router.py route "<task>" --stage build`, then read only the returned `reference` files relative to this skill root. Re-run with a new `--stage` when moving between phases. If no Python, inspect `assets/registry.json` and do this manually.
3. **Plan briefly**: define acceptance criteria and a sequence of independently verifiable milestones. For complex tasks read `references/planning.md`. Keep persistent state/checkpoints in the project, not the conversation context.
4. **Delegate selectively**: use the runtime's native subagents, if available, to route narrowly bounded independent tasks to the lowest-cost competent **configured** model. Never assume model names, prices, or unlimited quota. Small tasks often cost less without delegation. Read `references/delegation.md` only when delegation is available/useful.
5. **Implement** incrementally with appropriate pack(s). Preserve existing style and dependencies. Do not add remote skills at runtime or execute their install scripts without review/authorization.
6. **Verify** using real lint/build/tests; for UI also check responsive layout, accessibility, and RTL as appropriate, preferably with actual browser output. Do not infer success from commands you did not run.
7. **Independent review**: if another independent agent or model is available and worthwhile, let it review the diff + evidence, then fix issues and re-test, with bounded attempts. If unavailable, disclose that; do not claim independent review occurred.
8. **Deliver** results with files/commit references, actual test outcomes, remaining risks, and explicit blockers. Never claim 100% bug-free or "production ready" without evidence.

## Always-on economy and safety

- **Caveman is a core principle**: concise messages, targeted file reads, avoid repeating transcripts and giant logs. Preserve exact code, commands, errors, secrets warnings, and acceptance criteria. Caveman's official skill/proxy is an *optional external install*, not bundled or auto-installed here.
- Load references **only at point of need**; never load the entire registry or all reference files into the model context.
- Restrict parallel agents to separate files/tasks; coordinate commits and merges to avoid conflicts.
- Do not deploy, purchase, expose credentials, wipe data or silently modify remote infrastructure. Any external network activity follows runtime permissions and user authorization.
- If checks fail, keep a clear blocker, never silently downgrade acceptance criteria.

## Optional external CLI runner

For a user **who explicitly authorizes CLI execution**, `python <skill-root>/scripts/router.py doctor` detects local tools. `python <skill-root>/scripts/router.py run "<task>" --project <path>` is a **dry-run**; add `--execute` to invoke an already-installed and authenticated Claude Code, Codex, or OpenCode. See `references/delegation.md` for constraints. The helper does **not** replace the agent runtime or guarantee automatic multi-model routing.

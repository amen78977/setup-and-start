# Setup & Start

**One skill. The right tools at the right time.**

Portable, small-context orchestration skill for **Claude Code, Codex, OpenCode** and other Agent Skills-compatible assistants. It routes software tasks to a maximum of three relevant guidance packs at a time, uses Caveman-style token discipline, and specifies an implementation → tests → independent review → repair workflow.

> **Status: v1.0.0 — stable core release.** The one-entry skill, bounded phase router and opt-in local runner have automated regression and mocked end-to-end coverage. Optional model routing and autonomous CLI workflows remain environment-dependent: this project does **not** raise the model's intrinsic intelligence, guarantee zero bugs, or promise lower cost on every task. Its purpose is to improve coding-agent workflows, **not** compete directly with any app builder.

## Quick start — no Python needed for the skill itself

```bash
npx skills add amen78977/setup-and-start -s setup-and-start -a claude-code -a codex -a opencode -y
```

Run a supported agent and ask: **"Use setup-and-start: build a responsive Arabic inventory web app with tests."** The agent follows `skills/setup-and-start/SKILL.md` and loads only relevant `references/*.md` when needed. The `npx skills` installer is a third-party CLI; review its permissions before use. If an agent's installer target changes, consult `npx skills add ... --list` / current agent docs.

To install globally for all future projects, append `-g` to the command. To update an existing installation, run the same install command again. **Only one skill must be invoked by the user**; all the bundled specialty reference packs are selected on demand.

## Local zero-dependency helper (Python >= 3.10)

Clone/download this repo or install the skill and use its `scripts/router.py` path:

```bash
python skills/setup-and-start/scripts/router.py doctor
python skills/setup-and-start/scripts/router.py route "تصميم واجهة React عربية" --stage build
python skills/setup-and-start/scripts/router.py route "Create backend API with Postgres" --stage build
python skills/setup-and-start/scripts/router.py plan "Build an Arabic ecommerce website" --project .
```

The helper reads a **local, curated JSON registry** and returns at most three phase-relevant pack references. It inspects only known top-level project manifest names, not entire source trees or secret files. `plan` previews five phase-specific selections without invoking a model. The default skill guidance budget is 4,800 characters per invocation, not an unlimited prompt dump.

### Optional autonomous CLI workflow

```bash
# Dry-run: select builder/reviewer and packs without invoking a model.
python skills/setup-and-start/scripts/router.py run "Implement a search endpoint" --project .

# Execute only in a trusted project with local authenticated CLIs and permission.
python skills/setup-and-start/scripts/router.py run "Implement a search endpoint" --project . \
  --execute --check "python -m unittest discover -s tests" --attempts 2

# Or explicitly opt in to project-provided test/build scripts
python skills/setup-and-start/scripts/router.py run "Fix a search bug" --project . \
  --execute --auto-checks --attempts 2

# Capture supported CLI JSON usage counters, with optional local UI smoke evidence:
python skills/setup-and-start/scripts/router.py run "Polish the search UI" --project . \
  --execute --auto-checks --usage-telemetry --ui-url http://localhost:3000
```

**Windows PowerShell** (single-line syntax; POSIX backslash continuation above does not work in PowerShell):

```powershell
python skills/setup-and-start/scripts/router.py run "Fix the API tests" --project . --execute --auto-checks --attempts 2
```

`run` attempts implementation, real checks, and—if a *different* installed CLI exists—a bounded diff-based independent review. The reviewer receives **only selected changed source + check evidence**, not your complete repository. Changes committed by the builder are still found using the pre-run HEAD commit. It refuses to forward suspected credentials, partial/incomplete changesets or oversized diffs. The temporary reviewer directory is **NOT a hardened sandbox**, and secret scanning is best effort. A project-local run lock prevents simultaneous edits; stale locks require manual inspection. Feedback triggers bounded repair attempts, including retrying recoverable builder failures. Without meaningful checks **and** a valid independent review, the result is not fully verified. Re-run with `--resume` to use a failed checkpoint and increase `--attempts` if needed; the process is not an exactly-once job scheduler.

The runner refuses pre-existing dirty Git worktrees by default to avoid accidentally reviewing unrelated code. Commit/stash existing changes first, or explicitly use `--allow-dirty`. A real verification command (`--check` or `--auto-checks`) is required before paid execution; UI screenshots cannot replace functional tests. It refuses to count empty test suites as passing. If tests pass but independent review is unavailable, status is `tests_passed_review_unavailable` rather than a false "fully verified" result, and the runner stops instead of wasting repeated model invocations.

No reliable live prices, quotas or independent model-quality benchmarks are measured by this repo. Token usage can be parsed *only when supported CLIs return machine-readable counters*; unknown usage stays unknown. Model defaults inherit your installed CLIs unless you provide a model inventory. The runner **will** ask an existing CLI to edit your project when `--execute` is used; execute only on a trusted codebase. The local state file under `.setup-start/state.json` is Git-ignored and stores a **task hash** rather than the full task. Never put credentials into task prompts.

### Optional cost-aware model routing

Create your own inventory by adapting [docs/models.example.json](docs/models.example.json). **Do not use its placeholder identifiers or rates as real prices.** Then inspect the recommendation:

```bash
python skills/setup-and-start/scripts/router.py models "Review security-sensitive backend changes" --policy path/to/models.json --role review --mode economy
python skills/setup-and-start/scripts/router.py run "Refactor API" --project . --model-policy path/to/models.json --mode balanced
```

Modes: `economy` prioritizes price subject to a heuristic minimum strength, `balanced` uses price and strength, and `quality` prioritizes user-declared strength. The policy can select CLI-specific models for build and review, **not** invisibly provision accounts or reliably compare empirical capabilities. Native subagent routing remains runtime-dependent.

With a priced, user-owned model inventory and a sufficiently complex task, the runner **can automatically delegate one small discovery task** to a cheaper available model. This happens only if its forecast overhead is below 30% of the planned builder turn; it uses a separate temporary working directory, shares no project source automatically, and produces compact advisory JSON. `--no-delegation` disables it. Native subagent scheduling and parallel worktrees remain separate future capabilities.

`--max-estimated-usd 0.10` can reject a plan whose **rough forecast** exceeds your chosen threshold, but it **cannot cap actual provider billing**. `--usage-telemetry` requests structured CLI output and parses usage counters *where available*. Reports distinguish real returned counters from unknown values. Do not infer a saving from prompt-length comparisons alone.

### Optional real-browser UI quality loop

After you run your app at a loopback address, with Python Playwright and its browser already installed:

```bash
python skills/setup-and-start/scripts/browser_audit.py http://localhost:3000
```

This captures 390px mobile and 1440px desktop screenshots, plus a JSON report checking overflow, broken images, unlabeled controls and JavaScript exceptions. Reports live under `.setup-start/visual-evidence/`. Actual screenshot inspection and UX testing remain essential. Remote URLs require an explicit `--allow-remote` flag.

## Caveman (explicit priority)

Caveman is a first-class *policy*: concise responses, targeted loading, no lossy compression of source or debugging evidence. If the official [Caveman](https://github.com/JuliusBrussee/caveman) skill is already present, Setup & Start's instructions explicitly permit using its compatible output rules. Its optional proxy can be installed separately after license/privacy review. **We do not vendor or auto-activate the proxy, or misrepresent claimed savings as verified here.**

## Architecture

```
User request
  └─ setup-and-start/SKILL.md (single entry)
     ├─ doctor / identify permissions and CLIs
     ├─ router.py + curated assets/registry.json
     │  └─ up to three references for the CURRENT phase
     ├─ plan → build → tests → independent review → bounded repair
     ├─ optional separate providers / optional Caveman
     └─ evidence-based summary, not unsupported guarantees
```

## What is here / what's next

**Implemented:** portable one-entry skill, phase planner, Arabic/English matching, bounded guidance, Caveman-style context discipline, explicit model policies, conditional low-cost discovery delegation, optional structured usage accounting, optional CLI execution, opt-in checks and localhost browser QA, separate evidence-based reviewer, bounded repair attempts, checkpoints, run lock, no automatic third-party installs, cross-platform unit tests, **real subprocess integration tests using fake CLIs** and a local real-browser smoke test.

**Out of scope or not yet implemented:** reliable counters for every CLI/provider, empirical model capability calibration, provider quota discovery, true OS-level reviewer isolation, real billing caps, native parallel multi-agent worktrees, crash-proof job scheduling, and measured savings against no-skill runs on real coding tasks. See [roadmap](docs/ROADMAP.md).

### Verification

```bash
python -m unittest discover -s tests -v
python benchmarks/evaluate.py
```

GitHub Actions runs the standard-library tests and offline routing fixtures on every proposed change (Windows/Linux, Python 3.10/3.11/3.13). The offline benchmark tests **which packs are selected** and the number of **guidance characters** read; it does not measure model quality, real token usage, time or billing. A no-payment end-to-end test uses local fake agent CLIs; optional real-browser tests require installed Playwright/Chromium.

## External sources

[Agent Skills standard](https://agentskills.io/specification) · [Vercel skills CLI](https://github.com/vercel-labs/skills) · [Caveman](https://github.com/JuliusBrussee/caveman) · [Superpowers](https://github.com/obra/superpowers) · [Addy Osmani](https://github.com/addyosmani/agent-skills) · [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) · [Playwright CLI](https://github.com/microsoft/playwright-cli) · [Trail of Bits Skills](https://github.com/trailofbits/skills).

Repository-authored instructions are original; linked projects retain their own licenses. Contributions should never vendor external code without an explicit provenance/licensing review.

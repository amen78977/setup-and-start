# Setup & Start

**One skill. The right tools at the right time.**

Portable, small-context orchestration skill for **Claude Code, Codex, OpenCode** and other Agent Skills-compatible assistants. It routes software tasks to a maximum of three relevant guidance packs at a time, uses Caveman-style token discipline, and specifies an implementation → tests → independent review → repair workflow.

> **Status: experimental v0.2.** This is a real, testable single-entry skill/router with opt-in CLI execution, phase selection, deterministic project signals, checkpoint retries, evidence-based review, user-configured model policy and optional browser QA. It is **not** a guaranteed bug-free app builder, a hosted Lovable clone, a secure sandbox, or a magic unlimited-token interface. Providers and permissions must exist on your machine.

## Quick start — no Python needed for the skill itself

```bash
npx skills add amen78977/setup-and-start -s setup-and-start -a claude-code -a codex -a opencode -y
```

Run a supported agent and ask: **"Use setup-and-start: build a responsive Arabic inventory web app with tests."** The agent follows `skills/setup-and-start/SKILL.md` and loads only relevant `references/*.md` when needed. The `npx skills` installer is a third-party CLI; review its permissions before use. If an agent's installer target changes, consult `npx skills add ... --list` / current agent docs.

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
```

`run` attempts implementation, real checks, and—if a *different* installed CLI exists—a bounded diff-based independent review. The review command starts in a disposable directory and receives **only selected changed source + check evidence**, not your complete repository; it refuses to forward suspected credentials or oversized diffs. This is **not** a hardened sandbox. Feedback triggers bounded repair attempts. Without meaningful checks **and** a valid independent review, the status is **unverified**. Re-run the same command with `--resume` to use a failed checkpoint and increase `--attempts` if needed; a resume re-invokes the builder, it is not an exactly-once process manager.

No provider tokens, live prices, quotas or model quality are measured by this repo. Model defaults inherit your installed CLIs unless you provide a model inventory. The runner **will** ask an existing CLI to edit your project when `--execute` is used; execute only on a trusted codebase. The local state file under `.setup-start/state.json` is Git-ignored and stores a **task hash** rather than the full task. Never put credentials into task prompts.

### Optional cost-aware model routing

Create your own inventory by adapting [docs/models.example.json](docs/models.example.json). **Do not use its placeholder identifiers or rates as real prices.** Then inspect the recommendation:

```bash
python skills/setup-and-start/scripts/router.py models "Review security-sensitive backend changes" --policy path/to/models.json --role review --mode economy
python skills/setup-and-start/scripts/router.py run "Refactor API" --project . --model-policy path/to/models.json --mode balanced
```

Modes: `economy` prioritizes price subject to a heuristic minimum strength, `balanced` uses price and strength, and `quality` prioritizes user-declared strength. The policy can select CLI-specific models for build and review, **not** invisibly provision accounts or reliably compare empirical capabilities. Native subagent routing remains runtime-dependent.

### Optional real-browser UI quality loop

After you run your app at a loopback address, with Python Playwright and its browser already installed:

```bash
python skills/setup-and-start/scripts/browser_audit.py http://localhost:3000
```

This captures 390px mobile and 1440px desktop screenshots, plus a JSON report checking overflow, broken images, unlabeled controls and JavaScript exceptions. Reports live under `.setup-start/visual-evidence/`. Actual screenshot inspection and UX testing remain essential. Remote URLs require an explicit `--allow-remote` flag.

## Caveman (explicit priority)

Caveman is a first-class *policy*: concise responses, careful context selection, no lossy compression of logs necessary to debug. The official [Caveman](https://github.com/JuliusBrussee/caveman) skill/proxy can be installed separately after license/privacy review. **We don't vendor it, auto-install it, or misrepresent claimed savings as verified here.**

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

**Implemented:** portable skill, validated registry and phase planner, Arabic/English matching with exclusions, lightweight project detection, Caveman-style bounded guidance, doctor, dry-run, user-managed model policy, optional CLI execution, opt-in auto checks, separate evidence-limited reviewer, bounded repair, resumable checkpoint attempts, optional Playwright screenshots and cross-platform standard-library tests.

**Not yet implemented:** actual token metering, empirical cheapest-model routing, provider quota discovery, hard OS-level sandboxing, automatic hosted deployment, fully autonomous lifecycle job scheduling, downloading third-party skills, or measured benchmarks against Lovable. See [roadmap](docs/ROADMAP.md).

### Verification

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the standard-library tests on every proposed change.

## External sources

[Agent Skills standard](https://agentskills.io/specification) · [Vercel skills CLI](https://github.com/vercel-labs/skills) · [Caveman](https://github.com/JuliusBrussee/caveman) · [Superpowers](https://github.com/obra/superpowers) · [Addy Osmani](https://github.com/addyosmani/agent-skills) · [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) · [Playwright CLI](https://github.com/microsoft/playwright-cli) · [Trail of Bits Skills](https://github.com/trailofbits/skills).

Repository-authored instructions are original; linked projects retain their own licenses. Contributions should never vendor external code without an explicit provenance/licensing review.

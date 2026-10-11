# Setup & Start

**One skill. The right tools at the right time.**

Portable, small-context orchestration skill for **Claude Code, Codex, OpenCode** and other Agent Skills-compatible assistants. It routes software tasks to a maximum of three relevant guidance packs at a time, uses Caveman-style token discipline, and specifies an implementation → tests → independent review → repair workflow.

> **Status: experimental v0.1.** This repository ships a usable on-demand skill router and an opt-in *local CLI runner*, not a magical guaranteed bug-free app builder, native model router, or hosted Lovable clone. A CLI, models, permissions, browser and credentials are provided by the user and their environment. External skills are **not** downloaded or executed automatically.

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
```

The helper reads a **local, curated JSON registry** and returns up to three pack references. It never downloads remote instructions. The tool is useful even if only one coding agent is installed.

### Optional autonomous CLI workflow

```bash
# Dry-run: select builder/reviewer and packs without invoking a model.
python skills/setup-and-start/scripts/router.py run "Implement a search endpoint" --project .

# Execute only in a trusted project with local authenticated CLIs and permission.
python skills/setup-and-start/scripts/router.py run "Implement a search endpoint" --project . \
  --execute --check "python -m unittest discover -s tests" --attempts 2
```

`run` attempts implementation, user-supplied test commands and, if a *different* installed CLI is available, an advisory read-only independent review. Feedback can trigger bounded repair attempts. Without meaningful test commands **and** independent review, result is **unverified**, never falsely "complete". A reviewer prompt alone does not enforce filesystem read-only access: use a sandbox/worktree for isolation.

No real provider tokens, monetary costs or model quality are measured yet; model defaults come from already-installed CLIs. Optional per-role model IDs are read from environment variables (see `references/delegation.md`). No paid model or external proxy is provisioned by this repo. The runner **will** ask the existing CLI to change project files when `--execute` is used. The project task and short status are stored under `.setup-start/state.json` (git-ignored), so don't put secrets in task text.

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

**Implemented:** portable skill, curated registry, Arabic/English task matching, phase-filtered routing, doctor, dry-run, optional agent CLI execution, explicit test gates, independent reviewer selection across available CLIs, bounded repairs, state file, safety guidance and tests.

**Not yet implemented:** automatic token metering, empirical cheapest-model routing, crash-safe resume, provider quota discovery, true sandboxed reviewer enforcement, production-grade browser screenshot loop, auto-updating or executing third-party skills, deployment integrations, platform parity performance evaluations. See [roadmap](docs/ROADMAP.md).

### Verification

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the standard-library tests on every proposed change.

## External sources

[Agent Skills standard](https://agentskills.io/specification) · [Vercel skills CLI](https://github.com/vercel-labs/skills) · [Caveman](https://github.com/JuliusBrussee/caveman) · [Superpowers](https://github.com/obra/superpowers) · [Addy Osmani](https://github.com/addyosmani/agent-skills) · [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) · [Playwright CLI](https://github.com/microsoft/playwright-cli) · [Trail of Bits Skills](https://github.com/trailofbits/skills).

Repository-authored instructions are original; linked projects retain their own licenses. Contributions should never vendor external code without an explicit provenance/licensing review.

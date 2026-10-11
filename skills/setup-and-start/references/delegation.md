# Cost-aware model delegation, explicit inventory and CLI runner

Prefer native subagents when the runtime exposes them; a markdown skill alone cannot create provider accounts, change models or grant permissions.

- Classify subtasks by complexity, blast radius, expected token count and testability. Delegate cheap discovery, summary and simple tests only if spawning an agent is cheaper than doing them inline.
- Use names/models **actually configured** by the user; no invented model capability or current price table.
- Bound requests, context slices, maximum attempts, and timeout. Do not send secrets or full repositories to unknown endpoints.
- Give independent review to a different configured provider where practical. Two passes on one model are not independent verification.
- With `router.py models "<task>" --policy models.json --mode economy` an **explicit user-configured** model inventory is scored by role/complexity and USD-per-million token estimates. The heuristic strength scores are **user assertions**, not capability benchmarks; unknown rates are never treated as free.
- To let `run` choose model IDs, pass `--model-policy /path/to/models.json --mode economy`. No provider credentials, model subscriptions, prices or quotas are provisioned. Without a policy, inherit native CLI defaults.
- If only one CLI exists, the optional runner completes a builder pass but marks result **unverified** rather than faking review.

### Optional executable path

`python scripts/router.py doctor` detects `codex`, `claude`, `opencode`, optional Caveman.

`python scripts/router.py run "Implement a unit test" --project .` gives a dry-run.

`python scripts/router.py run "Implement a unit test" --project . --execute --check "python -m unittest discover -s tests"` invokes the configured CLI and checks, then supplies a **bounded changed-source diff** to a separate reviewer running in a disposable cwd if another CLI exists. A disposable cwd is **not** a security sandbox. If a diff is too large or contains suspected credentials, independent remote review is blocked. `--auto-checks` is an explicit opt-in to execute local npm/python scripts. With no check or reviewer, success remains unverified. `--resume` continues failed checkpoint attempts with matching task hash and additional retry budget.

Select provider models explicitly if needed using `SETUP_START_CODEX_BUILD_MODEL`, `SETUP_START_CLAUDE_BUILD_MODEL`, `SETUP_START_OPENCODE_BUILD_MODEL` (and corresponding `_REVIEW_MODEL`). Defaults inherit the CLI's model. This is configuration, not measured dynamic cost routing.

No providers, credentials, Caveman proxy, or tools are installed automatically. State is saved to `.setup-start/state.json`, containing task text and review summaries; **do not put secrets in task text**. Never commit the state directory.

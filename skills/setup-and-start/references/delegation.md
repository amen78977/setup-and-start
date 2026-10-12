# Cost-aware model delegation, explicit inventory and CLI runner

Prefer native subagents when the runtime exposes them; a markdown skill alone cannot create provider accounts, change models or grant permissions.

- Classify subtasks by complexity, blast radius, expected token count and testability. Delegate cheap discovery, summary and simple tests only if spawning an agent is cheaper than doing them inline.
- Use names/models **actually configured** by the user; no invented model capability or current price table.
- Bound requests, context slices, maximum attempts, and timeout. Do not send secrets or full repositories to unknown endpoints.
- Give independent review to a different configured provider where practical. Two passes on one model are not independent verification.
- If a priced explicit model inventory is present, the local runner may delegate one bounded, advisory discovery step to a cheaper agent automatically on nontrivial tasks. Other CLIs and their credentials must already exist. This is not general-purpose native parallel subagent execution.
- With `router.py models "<task>" --policy models.json --mode economy` an **explicit user-configured** model inventory is scored by role/complexity and USD-per-million token estimates. The heuristic strength scores are **user assertions**, not capability benchmarks; unknown rates are never treated as free.
- To let `run` choose model IDs, pass `--model-policy /path/to/models.json --mode economy`. No provider credentials, model subscriptions, prices or quotas are provisioned. Without a policy, inherit native CLI defaults.
- With a model policy, the runner prefers a separate provider for review and falls back to a different configured model on the same CLI in a fresh invocation. It never selects the builder's exact agent/model pair as the fallback reviewer. Without an eligible reviewer, tests passing remain explicitly unreviewed.

`economy` minimizes estimated price among qualified models. `balanced` ranks
estimated price divided by user-declared strength, allowing a modest premium for
quality. `quality` prioritizes strength. These are transparent heuristics, not
measured competence. Structured Codex turn and OpenCode step counters are summed;
explicit cumulative counters are used once. Unknown usage remains unknown.

Repair findings are retained in checkpoints so `--resume` receives the current
diagnosis, rather than restarting without failure context. Repair prompts replace
stale findings on each attempt instead of accumulating every previous log.

With a model inventory, failed attempts automatically use a strictly stronger
eligible build model on the same CLI when available. One candidate per strength
level forms a bounded ladder; attempts and timeouts remain unchanged. The
reviewer model is excluded. The dry-run shows the ladder and the forecast includes
its highest configured price. Use `--no-escalation` to keep the initial builder.
This relies on user-declared strength, not live model evaluation. Review is
deferred until functional checks pass to avoid paying to review known failures.

### Optional executable path

`python scripts/router.py doctor` detects `codex`, `claude`, `opencode`, optional Caveman.

`python scripts/router.py run "Implement a unit test" --project .` gives a dry-run.

`python scripts/router.py run "Implement a unit test" --project . --execute --check "python -m unittest discover -s tests"` invokes the configured CLI and checks, then supplies a **bounded changed-source diff** to a separate reviewer running in a disposable cwd if another CLI exists. A disposable cwd is **not** a security sandbox. If a diff is too large or contains suspected credentials, independent remote review is blocked. `--usage-telemetry` requests native JSON output and extracts counters when supported; unknown counter fields stay unknown. `--max-estimated-usd` only checks a rough configured forecast, not actual invoice cost. `--auto-checks` opts in to local npm/python scripts. With no check or reviewer, success remains unverified. `--resume` continues failed checkpoint attempts with matching task hash and additional retry budget.

Select provider models explicitly if needed using `SETUP_START_CODEX_BUILD_MODEL`, `SETUP_START_CLAUDE_BUILD_MODEL`, `SETUP_START_OPENCODE_BUILD_MODEL` (and corresponding `_REVIEW_MODEL`). Defaults inherit the CLI's model. This is configuration, not measured dynamic cost routing.

No providers, credentials, Caveman proxy, or tools are installed automatically. State is saved to `.setup-start/state.json`, containing a **task hash**, check results and review summaries, not the full task; **do not put secrets in task text or check commands**. Never commit the state directory. If review is unavailable but configured tests pass, the runner reports `tests_passed_review_unavailable` and does not spend extra repair turns merely because a reviewer is missing.

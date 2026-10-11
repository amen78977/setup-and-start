# Cost-aware model delegation and CLI runner

Prefer native subagents when the runtime exposes them; a markdown skill alone cannot create provider accounts, change models or grant permissions.

- Classify subtasks by complexity, blast radius, expected token count and testability. Delegate cheap discovery, summary and simple tests only if spawning an agent is cheaper than doing them inline.
- Use names/models **actually configured** by the user; no invented model capability or current price table.
- Bound requests, context slices, maximum attempts, and timeout. Do not send secrets or full repositories to unknown endpoints.
- Give independent review to a different configured provider where practical. Two passes on one model are not independent verification.
- If only one CLI exists, the optional runner completes a builder pass but marks result **unverified** rather than faking review.

### Optional executable path

`python scripts/router.py doctor` detects `codex`, `claude`, `opencode`, optional Caveman.

`python scripts/router.py run "Implement a unit test" --project .` gives a dry-run.

`python scripts/router.py run "Implement a unit test" --project . --execute --check "python -m unittest discover -s tests"` invokes the configured CLI and then any check command, and runs a separate read-only **prompt-based** review if a different CLI is found. It cannot sandbox the external CLI; run only inside a trusted project/container. With no check or independent reviewer, success remains unverified.

Select provider models explicitly if needed using `SETUP_START_CODEX_BUILD_MODEL`, `SETUP_START_CLAUDE_BUILD_MODEL`, `SETUP_START_OPENCODE_BUILD_MODEL` (and corresponding `_REVIEW_MODEL`). Defaults inherit the CLI's model. This is configuration, not measured dynamic cost routing.

No providers, credentials, Caveman proxy, or tools are installed automatically. State is saved to `.setup-start/state.json`, containing task text and review summaries; **do not put secrets in task text**. Never commit the state directory.

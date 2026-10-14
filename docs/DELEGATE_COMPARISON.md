# Comparison with amElnagdy/delegate-skills

Reviewed source: https://github.com/amElnagdy/delegate-skills

Revision: `3aa72d681a79e2a9d09bd9a316353003ae1cb4a7` (reviewed 2026-10-14).
License: MIT, copyright 2026 Ahmed Mohammed (amElnagdy). The comparison reads
the upstream README, Codex relay, brief/dispatch/queue references and fleet schema.
Upstream verification claims below are their reported evidence; this review did
not run paid providers or their full relay suite.

| Capability | delegate-skills | Setup & Start |
| --- | --- | --- |
| Implementer coverage | 18 CLI adapters with per-CLI permission caveats | Codex, Claude Code, OpenCode |
| Work assignment | Explicit named fleet lanes and direct implementer dispatch | Role/complexity/price policy, optional cheap discovery and separate reviewer |
| Coding delegation | Dedicated implementation relays | Existing builder CLI workflow; native delegation depends on host |
| Background lifecycle | Local artifacts, watchdogs, provider sessions; optional Codex background MCP | Bounded subprocess calls, checkpoints and host-managed waiting |
| Resume | Provider session identifiers and delta briefs | Task checkpoints and repair feedback; no provider-session continuation |
| Model economics | Configured implementer/model dials | User-priced selection, overhead heuristic and repair escalation |
| Verification | Orchestrator owns gates, review and landing | Executed-test outcomes, changed-source review and UI acceptance gates |
| Queues | Sequential dependency-ordered tasks and progress records in guidance | Bounded repair of one task; no general executable queue scheduler |
| Scope | Brief ownership and touched-file review; not OS containment | Self-contained task contract plus optional post-run scope tripwire |

The upstream is substantially broader as a delegation transport layer. Our
workflow is complementary, not a drop-in improved copy of every upstream adapter.
Neither project discovers and installs arbitrary internet agents automatically;
upstream fleet setup discovers already installed CLIs. Distinct CLI labels do
not establish distinct model providers or authenticated availability.

## Changes made after comparison

- Generate a self-contained task contract with owned paths, actual verification
  commands, constraints and a concise result contract before every builder call.
- Add repeatable `--allow-path` ownership for explicit files/subtrees. Validate
  paths before execution and expose the contract in dry-run output.
- Check ownership after successful or failed implementation and again after
  verification, including committed changes and rename source/destination paths.
- Stop as `scope_violation` before paying for review or repair; preserve all edits
  for inspection rather than reverting them automatically.
- Require the original ownership on resume and a clean Git baseline for scoped
  runs. Explicit dirty-baseline overrides cannot be combined with ownership.

This implementation was written independently. No upstream relay code, background
server, configuration or prompts were vendored or auto-installed. The source is
credited for its brief/ownership and orchestrator-led review design.

The scope tripwire inspects Git-visible changes (or a complete bounded non-Git
snapshot), not every filesystem write. Ignored files, outside-repository writes,
reverted edits and concurrent actors need OS isolation and independent oversight.
Contracts ask the worker not to commit; this is guidance, not a CLI-enforced
permission. Scope checks still inspect commits made since the baseline.

Future adapter/session/fleet integration should retain upstream permission
boundaries, validate exact CLI versions, preserve licensing and use host waiting
capabilities. A provider must not be advertised as supported just because a binary
name can be found on PATH.

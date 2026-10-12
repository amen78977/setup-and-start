# Measuring quality, cost and independence

The offline routing benchmark validates selection, not model quality or savings.
Use matched real tasks to measure the project's goals. No provider calls, model
accounts or payments are initiated by the comparison command.

1. Choose representative frontend, backend, security, debugging and multi-component
   tasks. Freeze acceptance tests independently of either implementation.
2. Run each task in clean equivalent environments, both with the skill and with
   the native agent alone. Match model versions and permissions; alternate ordering
   and repeat trials to expose variation. Preserve failing trials too.
3. Record actual provider counters/billing when available, elapsed seconds and
   human interventions. Use null for missing counters or price; do not substitute
   prompt-character estimates. Remove prompts, source, credentials and raw logs
   from the measurement file.
   Set `usage_complete: true` only when every invocation returned complete provider
   counters. Partial or unconfirmed token totals are excluded from comparison.
4. Export a JSON array in the format below. A pair must share task_id, repetition,
   acceptance_id and environment_id (a reproducible environment configuration ID).
5. Run `python benchmarks/compare_runs.py trials.json`. Inspect acceptance rates
   alongside token, cost, time and intervention changes. Lower usage with lower
   success is not an improvement. Unknown metrics stay unknown; inspect coverage
   before extrapolating results. This descriptive report provides no causal or
   statistical significance claim.

Record schema (replace illustrative identifiers and measurements with real data):

```json
[
  {"task_id":"api-01", "repetition":0, "variant":"baseline",
   "acceptance_id":"suite-v1", "environment_id":"same-config",
   "acceptance_passed":true, "human_interventions":1,
   "tokens":null, "usage_complete":false, "usd":null, "seconds":null},
  {"task_id":"api-01", "repetition":0, "variant":"skill",
   "acceptance_id":"suite-v1", "environment_id":"same-config",
   "acceptance_passed":true, "human_interventions":0,
   "tokens":null, "usage_complete":false, "usd":null, "seconds":null}
]
```

No real-world A/B saving has been established by unit tests. Publish measured
results and sample sizes before claiming a percentage improvement or universal
performance rating. Review independence also requires examining provider/model
identity; distinct CLI names alone do not establish distinct providers.

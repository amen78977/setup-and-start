# Evidence contract for autonomous completion

## Functional checks

Unittest/pytest and recognizable test-script outcomes must show actual non-skipped
tests executed. Empty suites, all-skipped/all-xfailed suites, unknown test counts,
failed commands and missing dependencies cannot certify acceptance. Custom
functional commands remain user-trusted checks: their exit status cannot establish
coverage automatically. Store concrete acceptance outcomes, not only a build PASS.

## UI tasks

UI tasks cannot obtain a verified result from source review and tests alone.
The runner requires current mobile/desktop capture to pass and an explicit visual
and user-journey inspection bound to the current source and screenshots.

Start the development server and save `.setup-start/runtime.json`:

```json
{"ui_url":"http://127.0.0.1:3000"}
```

The agent may instead supply `--ui-url`. Capture using the browser audit, inspect
both images with available vision tools, and actually exercise keyboard navigation,
responsive behavior and loading/empty/error/validation states. Use an independent
inspector when available; do not pretend that hashes prove an inspection occurred.
Playwright uses its installed browser, or system Chromium when its binary is absent.

Write `.setup-start/ui-review.json` (or supply `--ui-review-file`) with this schema:

```json
{
  "approved": true,
  "issues": [],
  "reviewer": "actual inspector identity",
  "source_sha256": "SHA256 from the current changed-source evidence",
  "screenshots": {"mobile":"SHA256 of mobile.png", "desktop":"SHA256 of desktop.png"},
  "checks": {
    "visual": "Describe observed hierarchy, typography, contrast and alignment.",
    "keyboard": "Describe the actual keyboard journey and its result.",
    "responsive": "Describe the mobile and desktop layouts inspected.",
    "states": "Describe exercised loading, empty, validation and error states."
  }
}
```

Image files live in `.setup-start/visual-evidence/`. Generate source evidence with
`evidence.collect(project, baseline=state['baseline'],
source_baseline=state.get('initial_file_sha256'))`; use its `sha256`, without
forwarding secret-looking content. Source or screenshot changes invalidate old
inspection evidence. Missing browser capability, uninspected artifacts or remaining
issues produce `acceptance_incomplete`, never a silently weakened success.
Artifact binding checks identity and freshness; it cannot authenticate the truth of
an inspector's assertions. This is a transparent limitation, not a visual score.

## Diagnosis and recovery

Timeouts, unavailable tools, dependencies, credentials, quota and connectivity
failures stop paid code repair with an explicit blocker. Implementation failures
and substantive reviewer findings may trigger a stronger configured repair model.
The attempt budget remains bounded. Invalid reviewer output is an infrastructure
failure, not evidence that another paid builder will help.

Discovery is marked attempted before invocation. Resume does not automatically
repeat discovery after invalid output or interruption. Checkpoints retain current
repair diagnostics, model selection, transitions and completed telemetry.

## Complete review

Git evidence and bounded full-tree non-Git evidence must include the changed
source. Exceeding traversal, byte, file or depth limits blocks remote approval.
Non-Git projects containing sensitive paths require local review or migration to
a Git project with properly ignored local credentials. Files are not silently
omitted to make review appear complete. A reviewer still sees a bounded diff;
cross-file invariants need tests or a trusted local reviewer with adequate context.

# Coding pack

- Read minimal relevant files; produce a smallest safe patch, not a full rewrite.
- Follow established conventions and write regression tests for the changed behavior.
- Prefer static analysis, type checks and targeted tests before expensive full builds.
- Run failing test first when feasible. Distinguish pre-existing failures from regressions.
- Document what changed, evidence, unresolved problems and whether a full test suite ran.
- Inspirations: `mattpocock/skills`, `obra/superpowers`, `amElnagdy/guard-skills`.

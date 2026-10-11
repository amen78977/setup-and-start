# Backend and database pack

- Define API contracts, schema migrations and invariants before adding endpoints.
- Validate inputs, enforce server-side authorization and prevent data leakage; secrets stay in environment/secret manager.
- Database changes need forward/backward-compatible migrations, test data, transaction boundaries and explicit rollback plans.
- Add tests for success, auth failure, invalid input, concurrency/retry and idempotency as appropriate.
- Do not touch production databases or credentials without authorization.
- Inspirations: official framework docs, Supabase Postgres best practices, OWASP.

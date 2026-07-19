# ADR 0001: Production Operational Baseline

- Status: Accepted
- Date: 2026-07-19
- Scope: Backend production hardening before the first unattended deployment

## Context

AeroC's v1 backend feature set and `/api/v1` product contract are frozen. The
remaining pre-deployment work is operational: ensuring that one process owns
scheduled collection, transient provider and database failures recover safely,
shutdown is bounded, and operators can distinguish process, database, and
scheduler health.

The current scheduler is embedded in the FastAPI lifespan. This ADR deliberately
keeps that architecture for the first production release rather than introducing
a second scheduler service during a hardening pass.

## Decisions

### Scheduler topology and ownership

The initial production topology has exactly one `api_scheduler` container,
exactly one Uvicorn worker, and exactly one replica. This is a deployment
invariant, not merely a Docker Compose example.

- Production configuration must explicitly set `AEROC_PROCESS_ROLE`.
- Supported initial roles are `api` and `api_scheduler`.
- `api` never owns a scheduler and remains ready without one.
- `api_scheduler` owns the scheduler and is not ready if the scheduler fails to
  start or becomes unhealthy.
- The deployment manifest fixes the `api_scheduler` worker and replica counts at
  one. The operations runbook prohibits scaling it.
- API horizontal scaling is prohibited until collection is moved to a dedicated
  scheduler process with single-owner enforcement.

The immediate startup collection is submitted as the same APScheduler job used
for interval execution. It is not called directly. Consequently,
`max_instances=1`, coalescing, job listeners, and scheduler diagnostics apply to
both startup and recurring executions.

Scheduler policy:

- run once immediately on startup;
- interval: 60 minutes by default;
- `max_instances=1`;
- `coalesce=true`;
- misfire grace: 300 seconds by default.

### Collection transaction semantics

Collection cycles may partially succeed. Each city is an independent atomic
unit and uses a distinct SQLAlchemy session and transaction. An exhausted error
for one city is recorded and collection continues with the next city. A failed
session is rolled back and closed before another city begins, so it cannot poison
subsequent work.

Provider retries are bounded and apply only to transient failures: connection
and timeout failures, HTTP 429, and HTTP 5xx. Permanent HTTP 4xx and payload
validation failures are not retried. Database writes remain idempotent through
the existing unique constraints and conflict handling.

### Origin model

The production dashboard and backend use a same-origin reverse proxy. Production
CORS is therefore disabled. The public `/api/v1` routes and response contracts
remain unchanged. Operational routes live outside that prefix.

### PostgreSQL and shutdown targets

The target database major version is PostgreSQL 17. The production patch release
or managed-service version is pinned and recorded during release qualification.

The application shutdown budget is 90 seconds. The deployment platform provides
a 120-second termination grace period as the final enforcement boundary.

Bounded shutdown is cooperative:

1. mark the application and scheduler as shutting down;
2. signal the active collection cancellation event;
3. stop accepting new scheduled executions;
4. the retry and city loops check cancellation before attempts, during interruptible
   backoff, and between cities;
5. wait only within the application shutdown budget;
6. if work does not finish, return control to process termination; the platform
   grace period is the final hard stop and PostgreSQL rolls back an interrupted
   transaction.

Calling `scheduler.shutdown(wait=True)` by itself is not considered a bounded
shutdown mechanism.

### Database TLS

Local development defaults to `DATABASE_SSLMODE=prefer`. Production must
explicitly choose one of:

- `require`, with documentation that transport is encrypted but the database
  server certificate identity is not verified; or
- `verify-full`, with `DATABASE_SSLROOTCERT` pointing to the mounted provider CA
  certificate and hostname verification enabled.

If `verify-full` is selected without a readable CA certificate path, production
configuration is invalid. AeroC never silently downgrades the configured TLS
mode.

### Health semantics

Operational surfaces are outside `/api/v1`:

- `/health/live` reports process liveness and has no database dependency;
- `/health/ready` checks database connectivity and role-specific runtime state;
- `/ops/status` exposes sanitized process, database, scheduler, and last-run state.

An `api` process does not fail readiness because it has no scheduler. An
`api_scheduler` process fails readiness if its scheduler is expected but not
healthy.

## Consequences

- One failing city no longer blocks collection for all other cities.
- A collection cycle can be reported as partial and must include per-city outcome
  counts in operational logs and status.
- The initial API deployment cannot be horizontally scaled.
- A future dedicated scheduler is required before API horizontal scaling.
- The deployment platform remains responsible for enforcing the final shutdown
  deadline, TLS/CA mounting, secrets, backups, and restore testing.
- Gates 1 through 5 and Gate 7 are code/test work. Gate 6 and the backup/restore
  portions of Gate 8 are deployment-platform work after hosting is selected.

## Verification requirements

- Configuration tests cover roles, production secrets, positive bounds, and TLS
  CA requirements.
- PostgreSQL integration tests cover migrations, seed idempotency, duplicate
  collection, per-city rollback, stale connection recovery, and restart.
- Scheduler tests prove startup and recurring work share one APScheduler job,
  overlap is rejected, failures do not disable later runs, and shutdown observes
  cooperative cancellation.
- Health tests prove role-aware readiness and database-outage recovery.
- The smoke-test outage check must distinguish an expected HTTP failure from an
  unexpected successful readiness response; its own assertion must never be
  swallowed by the failure handler.

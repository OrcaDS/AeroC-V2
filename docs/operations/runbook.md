# AeroC Operations Runbook

## Production topology invariant

The first production release runs exactly one `api_scheduler` container with
exactly one Uvicorn worker and exactly one replica.

Do not scale the `api_scheduler` container horizontally and do not start Uvicorn
with more than one worker. `max_instances=1` protects one APScheduler instance;
it is not a distributed lock. Database idempotency prevents duplicate rows but
does not prevent duplicate provider calls or competing scheduler processes.

API horizontal scaling is prohibited until collection has been moved into a
dedicated, single-owner scheduler process. At that point, API processes must use
`AEROC_PROCESS_ROLE=api` and the dedicated scheduler must be deployed separately.

## Process roles

- `api`: serves HTTP and has no scheduler. Readiness depends on PostgreSQL, not
  scheduler state.
- `api_scheduler`: serves HTTP and owns scheduled collection. Readiness requires
  PostgreSQL, a live scheduler thread, and collection freshness after the startup
  grace period.

Production must explicitly configure `AEROC_PROCESS_ROLE`. The
`api_scheduler` role also requires `AEROC_WEB_WORKERS=1`.

## Shutdown

The application shutdown budget is 90 seconds and the deployment-platform
termination grace period is 120 seconds. Shutdown signals cooperative
cancellation, prevents new APScheduler executions, interrupts retry backoff,
checks cancellation between cities, and waits only for the application budget.
The platform grace period is the final enforcement boundary.

If `event=scheduler_shutdown_timed_out` is logged, verify database integrity after
restart. PostgreSQL must contain either a complete observation with all pollutant
values or no observation for the interrupted city.

## Database TLS

Production must deliberately choose `require`, `verify-ca`, or `verify-full`.

- `require` encrypts transport but does not verify the server identity. Record
  that trust decision with the selected hosting environment.
- `verify-ca` and `verify-full` require the hosting provider CA certificate to be
  mounted read-only and referenced by `DATABASE_SSLROOTCERT`.
- Prefer `verify-full` when the provider supplies a stable database hostname and
  CA chain. It verifies both the CA and hostname.

AeroC refuses to start with a certificate-verifying mode if the configured CA
file is missing.

## Operational endpoints

- `GET /health/live`: process-only liveness.
- `GET /health/ready`: PostgreSQL and role-aware runtime readiness.
- `GET /ops/status`: sanitized scheduler and latest collection diagnostics.

These are operational surfaces outside the frozen `/api/v1` product contract.

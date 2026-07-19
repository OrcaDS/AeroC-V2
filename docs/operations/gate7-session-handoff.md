# AeroC Gate 7 Session Handoff

- Handoff date: 2026-07-19
- Repository: `C:\Users\KurtO\Documents\AeroC-V2`
- Branch at handoff: `main`
- Baseline commit at the start of hardening: `9443a9c`
- Current task: Gate 7 complete; Gate 6 hosting selection is the next release gate

## User intent

The backend feature set and `/api/v1` product contract are frozen. Work is an
operational hardening pass only. Do not add environmental features, redesign AQI
or trends, add authentication, alerts, or notifications, or change `/api/v1`
unless required for production correctness.

The user accepted P0 hardening and requested Gate 7 next:

1. build and run the PostgreSQL 17/Compose migrate–seed–collect–restart harness;
2. retain build and runtime logs, health responses, Alembic revision, and
   integrity-query output as staging release evidence; and
3. leave Gate 6 hosting manifests and Gate 8 platform TLS/secrets/backups for
   later, after hosting selection.

## Accepted operational decisions

The binding decisions are recorded in
[`docs/adr/0001-production-operational-baseline.md`](../adr/0001-production-operational-baseline.md).

- Initial production topology: exactly one `api_scheduler` container, exactly
  one Uvicorn worker, and exactly one replica.
- This is a deployment invariant. Do not scale `api_scheduler`.
- A dedicated scheduler is required before API horizontal scaling.
- Immediate startup collection and interval collection use the same APScheduler
  job, so `max_instances=1` governs both.
- Collection uses a distinct SQLAlchemy session and transaction per city.
- A failed city rolls back independently and does not poison later cities.
- Production uses a same-origin reverse proxy; `/api/v1` remains unchanged.
- Target database major: PostgreSQL 17.
- Application shutdown budget: 90 seconds.
- Platform termination grace: 120 seconds.
- Shutdown is cooperative; the platform grace period is the final boundary.
- Production database TLS deliberately uses `require`, `verify-ca`, or
  `verify-full`. Certificate-verifying modes require a mounted CA file.
- Readiness is role-aware: `api` does not require a scheduler;
  `api_scheduler` does.

## P0 implementation completed

P0 was implemented in this order:

1. configuration validation;
2. database engine/session lifecycle;
3. per-city collection and provider retries;
4. scheduler lifecycle and bounded shutdown; and
5. operational health surfaces.

Important files include:

- `backend/app/config/settings.py`
- `backend/app/database/session.py`
- `backend/alembic/env.py`
- `backend/app/ingestion/collectors/open_meteo.py`
- `backend/app/runtime/collection_runner.py`
- `backend/app/runtime/collection_scheduler.py`
- `backend/app/api/ops.py`
- `backend/app/main.py`
- `backend/.env.example`
- `docs/operations/runbook.md`

Operational routes were added outside the frozen product API:

- `GET /health/live`
- `GET /health/ready`
- `GET /ops/status`

The latest complete backend test run passed inside the exact Gate 7 deployment
image after Gate 7 fixes and added service regression coverage:

```text
53 passed, 1 warning in 0.70s
```

The warning is the previously accepted Starlette TestClient/HTTPX deprecation
warning and remains deferred maintenance.

## Gate 7 harness implemented

The following reusable Gate 7 artifacts now exist:

- `backend/Dockerfile`
- `backend/.dockerignore`
- `compose.smoke.yml`
- `scripts/run_gate7_smoke.ps1`
- `backend/tests/smoke/mock_open_meteo.py`
- `backend/tests/smoke/partial_integrity.sql`
- `backend/tests/smoke/integrity.sql`
- `docs/operations/gate7-smoke.md`

The Compose stack is isolated with project name `aeroc-gate7`, a dedicated
volume, and loopback-only ports:

- API: `127.0.0.1:18080`
- mock provider: `127.0.0.1:18081`
- PostgreSQL: `127.0.0.1:55432`

The harness is designed to verify:

1. PostgreSQL 17 startup;
2. Alembic migration to revision `d8a002901c1f`;
3. seed idempotency;
4. deterministic initial collection;
5. duplicate collection idempotency;
6. a partial city failure with seven successful city transactions;
7. recovery of the failed city;
8. exactly one scheduler owner per process generation;
9. application restart;
10. role-aware health responses;
11. PostgreSQL outage and automatic readiness recovery;
12. a recurring interval execution; and
13. final database integrity checks.

The readiness-outage assertion captures the response body and numeric HTTP
status with `curl.exe`, avoiding Windows PowerShell 5.1 exception-shape
differences while strictly requiring HTTP 503.

The successful stack is intentionally left running for inspection. Cleanup is
limited to its isolated resources:

```powershell
docker compose -p aeroc-gate7 -f compose.smoke.yml down --volumes
```

## Gate 7 result

Gate 7 passed against Docker Desktop 4.82.0, Docker Engine 29.6.1 configured for
Linux containers, Compose 5.3.0, and PostgreSQL 17.10. The successful retained
evidence is:

```text
staging-evidence/gate7-20260719-221523/
```

Verified outcomes:

- `RESULT.txt` records `status=PASS`;
- the deployment image tests record `53 passed` and `RESULT.txt` records
  `tests=PASS`;
- the tested image ID is
  `sha256:a2d849a0968a1e6f292c5363a4f43e7bcf03681739e14c7cae9be437c1ccae49`;
- Alembic reached `d8a002901c1f`;
- initial and post-restart readiness reported `ready`;
- readiness returned HTTP 503 during the PostgreSQL outage and automatically
  recovered after PostgreSQL restarted;
- seven cities committed independently while Bandung failed, then Bandung
  recovered;
- final integrity contains 8 cities, 16 observations, and 96 pollutant rows,
  with no duplicates, incomplete aggregates, or orphans;
- API logs contain one `scheduler_started` event per process generation; and
- scheduled collection event count increased from 2 to 3 at the recurring
  one-minute interval.

The successful isolated stack remains running for inspection. Clean it up only
with:

```powershell
docker compose -p aeroc-gate7 -f compose.smoke.yml down --volumes
```

Earlier failed evidence directories remain retained. They document the original
Docker-engine preflight blocker and defects found and fixed while exercising the
harness; they do not supersede the successful evidence above.

Two Gate 7 fixes were required:

- `CollectionService.collect_city` had a misplaced early `return created`, which
  made the collection workflow unreachable. The return now occurs after
  persistence, with focused created/duplicate regression coverage.
- The harness now tolerates normal Docker Compose progress on native stderr in
  Windows PowerShell 5.1 and validates the outage status without depending on
  `Invoke-WebRequest` exception internals.

## Working tree safety

The working tree was already dirty before this Gate 7 work. The following
dashboard changes belong to the user and must not be reverted or overwritten:

- `dashboard/src/App.css`
- `dashboard/src/App.tsx`
- `dashboard/src/api.ts`

The `.codex/` directory is also untracked and must be left alone.

Backend P0, Gate 7 artifacts, ADR, runbook, and evidence directories are current
session work and are not committed. Do not use destructive Git commands or clean
the working tree broadly.

## Remaining work after Gate 7

- Gate 6: select hosting and create the production deployment manifest, fixing
  `api_scheduler` replicas and Uvicorn workers to one.
- Gate 8 platform items: production TLS, secrets, backups, retention, and a
  documented restore test.
- Deferred: Starlette TestClient/HTTPX deprecation maintenance.

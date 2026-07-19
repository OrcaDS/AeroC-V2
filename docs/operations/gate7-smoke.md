# Gate 7 PostgreSQL Smoke Harness

The Gate 7 harness validates AeroC against PostgreSQL 17 with deterministic
provider responses. It uses the isolated Compose project name `aeroc-gate7`, a
dedicated volume, and loopback-only ports.

## Prerequisites

- Docker Desktop or Docker Engine configured for Linux containers.
- Windows hosts using Docker Desktop must have Virtual Machine Platform/WSL 2
  enabled and may require a reboot after enabling it.
- Ports `18080`, `18081`, and `55432` must be available.

## Run

From the repository root:

```powershell
.\scripts\run_gate7_smoke.ps1
```

The runner performs:

1. isolated volume cleanup;
2. image build, immutable image-ID capture, and backend tests inside that image;
3. PostgreSQL 17 startup;
4. migration to Alembic head;
5. double seed verification;
6. deterministic collection and duplicate collection;
7. a partial city failure followed by recovery;
8. application startup and single scheduler-owner verification;
9. application restart;
10. PostgreSQL outage/readiness failure and automatic recovery;
11. a recurring interval execution; and
12. final integrity queries.

The database-outage assertion captures the readiness response body and numeric
HTTP status directly, and requires HTTP 503 before PostgreSQL is restarted.

## Evidence

Every run creates a timestamped directory under `staging-evidence/`, including
failed preflight runs. Evidence includes:

- Git and Docker metadata;
- resolved Compose configuration;
- build, deployment-image test, migration, seed, and collection logs;
- the built image tag and immutable image ID;
- Alembic revision;
- health and operational-status responses;
- scheduler logs before and after restart;
- database-outage and recovery results;
- mock-provider request statistics;
- partial and final integrity-query output; and
- `RESULT.txt` with `PASS` or `FAIL`.

The successful stack is left running for inspection. Remove only its isolated
resources with:

```powershell
docker compose -p aeroc-gate7 -f compose.smoke.yml down --volumes
```

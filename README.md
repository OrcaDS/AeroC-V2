# AeroC

> Environmental intelligence for confident public decisions.

AeroC is an environmental monitoring platform that turns provider air-quality snapshots into an evidence-led monitoring experience. Open-Meteo supplies the underlying model data; AeroC stores the first captured snapshot for each city and valid hour, then exposes estimated AQI, trends, history, and a map-first monitoring product.

## Product focus

The product answers three questions in order:

1. Where should I look right now?
2. What is changing?
3. What evidence supports that interpretation?

The Monitoring Overview is map-first. City Intelligence provides the detailed investigation view. Raw pollutant values remain available as evidence rather than becoming the primary interface.

## Architecture

```text
Open-Meteo air-quality forecast
        |
        v
Collector -> normalized DTO -> CollectionService -> repositories
        |                                              |
        +----------------------------------------------v
                                           PostgreSQL
                                                |
                           AQI / trend / dashboard services
                                                |
                                             FastAPI
                                                |
                                  React monitoring dashboard
```

The scheduler runs inside the FastAPI lifespan and invokes the reusable collection runner. The runner owns the transaction lifecycle; the scheduler only schedules work.

## Repository layout

```text
backend/                 FastAPI, SQLAlchemy, Alembic, ingestion, tests
dashboard/               React + TypeScript + Vite monitoring application
docs/                    Architecture and data-contract documentation
frontend wireframe/      Approved product-design references
docker-compose.yml       Local PostgreSQL service
```

## Backend capabilities

- Scheduled Open-Meteo collection for active cities
- UTC-normalized provider-valid timestamps
- Idempotent first-snapshot persistence for `(city, observed_at, source)`
- Normalized `cities`, `observations`, and `observation_values` schema
- Dashboard, latest-observation, history, and trend endpoints
- Estimated EPA-style PM2.5/PM10 AQI with explicit limitations

### API surface

All routes are prefixed with `/api/v1`.

- `GET /dashboard`
- `GET /cities`
- `GET /cities/{id}`
- `GET /cities/{id}/latest`
- `GET /cities/{id}/history`
- `GET /cities/{id}/trends?days=1`

## Important data contract

An AeroC observation is the **first successfully collected provider forecast snapshot** for a given `(city, observed_at, source)` key. It is immutable within AeroC. Forecast revision tracking is intentionally out of scope for v1.

AQI is explicitly marked as an estimate. It is based on available PM2.5 and PM10 model observations, is not an official EPA AQI, does not apply required 24-hour or NowCast averaging, and does not include gaseous-pollutant sub-indices.

## Local development

### 1. Start PostgreSQL

```powershell
docker compose up -d
```

### 2. Configure and start the backend

From `backend/`, create `.env` from `.env.example` and ensure its database settings match the local PostgreSQL service. Then install dependencies, migrate, seed, collect, and start FastAPI:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_cities
python -m scripts.collect_once
uvicorn app.main:app --reload
```

### 3. Start the dashboard

From `dashboard/`:

```powershell
npm.cmd install
npm.cmd run dev
```

Vite proxies `/api` to `http://localhost:8000` during local development. Set `VITE_API_URL` when the API is hosted elsewhere; include the `/api/v1` path.

## Verification

```powershell
# Backend
.\backend\.venv\Scripts\pytest.exe backend\tests -q

# Frontend
Set-Location dashboard
npm.cmd run build
npm.cmd run lint
```

## Current status

The backend contract is frozen. Current development is frontend-first: the UI may expose concrete API friction or correctness issues, but backend changes are not made speculatively.

The frontend currently implements the Monitoring Overview and City Intelligence views against the existing API contract.

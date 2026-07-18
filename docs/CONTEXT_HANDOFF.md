# AeroC-V2 Context Handoff

## Project Overview

AeroC-V2 is an environmental monitoring platform that collects environmental observations from external providers (currently Open-Meteo), stores them in PostgreSQL, computes higher-level environmental insights, and exposes consumer-oriented APIs for dashboards and future frontend applications.

The goal is not to mirror Open-Meteo. AeroC should become an interpretation layer that transforms raw environmental measurements into meaningful information.

## Current Architecture

The backend is built with:

- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Alembic
- Repository pattern
- Service layer
- Domain models
- Pydantic schemas
- Scheduled collectors

Current architecture follows:

```text
Collector
    ↓
DTO
    ↓
Repository
    ↓
Database
    ↓
Service Layer
    ↓
API
```

Important rules:

- API routes contain no business logic.
- Repositories perform persistence.
- Services implement domain logic.
- Schemas only define contracts.
- Domain objects model business concepts.

Representation mapping happens only at the API boundary.

## Current Capabilities

### ETL

Implemented.

Current flow:

```text
Scheduler
→ Collector
→ DTO
→ Repository
→ PostgreSQL
```

Running:

```bash
python -m scripts.collect_once
```

collects observations for all seeded cities.

Database currently stores:

- Cities
- Observations
- ObservationValues

### API

Implemented.

Current endpoints include:

- `GET /cities`
- `GET /cities/{id}`
- `GET /cities/{id}/latest`
- `GET /cities/{id}/history`
- `GET /cities/{id}/trends`
- `GET /dashboard`

The API is intentionally consumer-shaped, not database-shaped.

### AQI

Implemented.

Important design decisions:

- AQI is a first-class domain capability.
- Implemented as:

```text
AqiService
    ↓
EpaUsAqiCalculator
```

- API never contains AQI logic.
- AQI is computed on read, not persisted.
- Responses explicitly mark the assessment as estimated. It is derived from
  available PM2.5/PM10 model observations and is not an official EPA AQI:
  AeroC does not yet apply the required 24-hour or NowCast averaging and does
  not calculate gaseous pollutant sub-indices.
- Current implementation intentionally uses only PM2.5 and PM10 because Open-Meteo does not currently expose the averaging semantics required for EPA-compliant calculations of ozone, CO, NO₂, and SO₂.

The response explicitly identifies:

- `standard = "epa_us"`

and documents this limitation.

### Trend Analysis

Implemented.

Trend Analysis is also a domain capability.

Architecture:

```text
TrendService
        ↓
WindowTrendCalculator
        ↓
TrendDirectionPolicy
TrendSufficiencyPolicy
```

Current implementation compares two observation windows.

Each pollutant reports:

- averages
- absolute change
- percent change
- direction
- observation counts
- status when insufficient data

No forecasting has been implemented.

### Dashboard

Implemented.

Dashboard endpoint aggregates information into:

- `summary`
- `leaders`
- `cities[]`

instead of exposing raw database rows.

Dashboard powers:

- KPI cards
- map markers
- leaderboards
- latest observations

Current dashboard works end-to-end.

## Testing

The backend is heavily tested.

Current status:

- integration tests
- unit tests
- endpoint tests

All tests currently pass.

## Development Philosophy

The project intentionally prioritizes:

- explicit contracts
- domain modeling
- clean architecture
- maintainability
- correctness over convenience

We avoid:

- putting logic inside routers
- leaking ORM models
- persistence-driven APIs
- premature abstraction

We only add new capabilities when they clearly increase product value.

## Current State

The backend is now stable.

The ETL pipeline works.

The scheduler successfully collects data.

The API exposes consumer-oriented contracts.

AQI and Trend Analysis are implemented.

Dashboard aggregation works.

At this point AeroC has evolved beyond a weather-data wrapper into an environmental intelligence backend.

## Working Style

Act as a senior backend engineer and technical reviewer.

Challenge assumptions when appropriate, but prefer simple, maintainable solutions over over-engineering.

When proposing new features:

1. Start from the product value.
2. Design the domain model.
3. Freeze the API contract.
4. Implement the service layer.
5. Add tests.
6. Finally expose the feature through the API.

Do not recommend adding infrastructure or abstractions unless there is a concrete engineering reason.

Before proposing the next feature, evaluate whether it genuinely increases AeroC's value proposition beyond what Open-Meteo already provides. If it does not, say so and recommend a higher-impact direction instead.

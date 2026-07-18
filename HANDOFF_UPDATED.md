# AeroC Platform Handoff (Codex)

## Executive Summary

AeroC has evolved from an ETL backend into an **Environmental
Intelligence Platform**. The backend is considered **architecturally
stable**. Development should now be driven by product experience rather
than backend expansion.

## Product Vision

Open-Meteo provides measurements. AeroC provides interpretation: - AQI
assessment - Trend analysis - Dashboard aggregation - Monitoring
workflows

Backend changes should only occur if frontend implementation exposes
genuine friction.

## Guiding Principles

1.  Business capabilities over CRUD.
2.  Collectors perform HTTP only.
3.  DTOs isolate providers.
4.  Services own business logic.
5.  Repositories own persistence.
6.  API adapts domain models.
7.  Frontend never duplicates environmental logic.
8.  Product drives architecture.

## Architecture

``` text
Open-Meteo
  ↓
Collector
  ↓
DTO
  ↓
CollectionService
  ↓
Repositories
  ↓
PostgreSQL
  ↓
Business Services
  ├─ DashboardService
  ├─ AqiService
  └─ TrendService
  ↓
FastAPI
  ↓
Frontend
```

## Runtime

APScheduler runs inside FastAPI lifespan. CollectionScheduler -\>
CollectionRunner -\> CollectionService. Runner owns session lifecycle
(create, commit, rollback, close). Scheduler is intentionally thin: -
max_instances=1 - coalesce=True - single backend process assumption

## Database

Normalized schema: - cities - observations - observation_values

## Domain Capabilities

### AQI

-   EPA US v1
-   Estimated assessment derived from PM2.5/PM10 forecast snapshots only
-   Not an official EPA AQI: required 24-hour/NowCast averaging and gaseous
    pollutant sub-indices are not yet available
-   First-class object
-   No advisories
-   Computed on read

### Trends

Window comparison: - current vs baseline - averages - absolute/percent
change - direction policy - sufficiency policy -
status=insufficient_data when appropriate

## API Surface

-   GET /cities
-   GET /cities/{id}
-   GET /cities/{id}/latest
-   GET /cities/{id}/history
-   GET /cities/{id}/trends
-   GET /dashboard

These are consumer-oriented contracts.

## Current Status

Completed: - ingestion - persistence - API - scheduler - dashboard
aggregation - AQI - trends - automated collection - 30+ tests

Backend is frozen unless UI reveals real friction.

## Frontend Philosophy

The UI should answer: 1. Where should I look? 2. Why is this happening?
3. What evidence supports it?

AQI is the primary language. Raw pollutants support interpretation.

## User Workflows

Environmental Officer: Monitoring Overview → Map → Leaders → City

City Analyst: City → AQI → Trends → History

Researcher: City → History → Time-series

## Information Architecture

Monitoring Overview - Summary - Map - Leaders - Watchlist

City Intelligence - Status - AQI - Current Conditions - Trends - History

## Component Mapping

/dashboard → overview /latest → status /trends → trend cards /history →
charts

## Roadmap

Current phase: 1. Freeze frontend UX 2. Wireframes 3. Component tree 4.
Implement frontend 5. Only revise backend when proven necessary

Future: - Alerts - Forecasting - Multi-provider ingestion - Risk
engine - Authentication

## Codex Guidance

Treat the backend as stable. Challenge assumptions. Prefer simple,
explicit designs. Maintain separation of concerns. Optimize for product
value over infrastructure.

## Observation Persistence Contract

An observation is AeroC's first successfully collected Open-Meteo forecast
snapshot for a `(city, observed_at, source)` key. It is immutable within
AeroC: repeated collection attempts do not overwrite it. Forecast revision
tracking is out of scope for v1 and would require distinct concepts such as
model run or issued time.

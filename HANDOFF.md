1. Executive Summary

What AeroC is.

Not:

Environmental monitoring backend.

Instead:

AeroC is an Environmental Intelligence Platform whose backend has reached architectural stability. The current focus is transforming those capabilities into a monitoring product.

2. Product Vision

Explain that AeroC is not trying to compete with Open-Meteo.

Open-Meteo provides measurements.

AeroC provides:

interpretation
aggregation
AQI
trend analysis
monitoring workflows

This distinction is extremely important.

3. Guiding Principles

Keep these.

They've become the DNA of the project.

Things like:

Business capabilities over CRUD.
Domain logic belongs in services.
Representation belongs in API.
Frontend never duplicates environmental logic.
Product drives architecture, not vice versa.
4. Backend Architecture

Update this.

Instead of stopping at Collector → Repository, include everything.

Example:

Open-Meteo
      │
Collector
      │
DTO
      │
Collection Service
      │
Repositories
      │
PostgreSQL
      │
Business Services
      │
├── DashboardService
├── AqiService
├── TrendService
      │
FastAPI
      │
Frontend
5. Runtime Architecture

This didn't exist before.

Document:

FastAPI Lifespan

↓

CollectionScheduler (APScheduler)

↓

CollectionRunner

↓

CollectionService

↓

Repositories

↓

Commit

Also explain:

max_instances=1
coalesce=True
scheduler is single-process
runner is reusable
collect_once.py reuses runner

This is important institutional knowledge.

6. Current API Surface

Instead of planned endpoints, document what's real.

GET /cities

GET /cities/{id}

GET /cities/{id}/latest

GET /cities/{id}/history

GET /cities/{id}/trends

GET /dashboard

Document what each endpoint exists to answer.

Not just what it returns.

7. Domain Capabilities

This section didn't exist before.

Document:

AQI

Purpose.

Design.

Limitations.

EPA assumptions.

Primary pollutant.

Subindices.

No advisories.

Trends

Window comparison.

Threshold policy.

Sufficiency policy.

Status handling.

No forecasting.

8. Scheduler

Document:

CollectionRunner
CollectionScheduler
APScheduler
lifespan
interval config

This is now production behavior.

9. Testing

Mention:

30+ passing tests.

Coverage includes:

repositories
endpoints
dashboard
AQI
trends
scheduler
runner

That's impressive and worth documenting.

10. Product Status

This is probably the most important new section.

Something like:

Current maturity:

✓ Ingestion
✓ Persistence
✓ API
✓ Scheduler
✓ Dashboard aggregation
✓ AQI
✓ Trend analysis

Current bottleneck:

No user-facing product.

That's the truth.

11. Frozen Backend

Explicitly state:

Unless frontend implementation exposes genuine friction:

Do not:

redesign endpoints
redesign schemas
redesign services
redesign scheduler

Treat backend as stable.

This is incredibly important.

12. Frontend Philosophy

Brand new section.

Explain:

The frontend exists to answer:

Where should I look?

Why is this happening?

What evidence supports it?

Monitoring first.

Diagnosis second.

Evidence third.

13. User Workflows

Environmental Officer

↓

Monitoring Overview

City Analyst

↓

City Detail

Researcher

↓

History

14. Information Architecture

Monitoring Overview

↓

Map

↓

Leaders

↓

Watchlist

↓

City Detail

↓

History

Exactly like you've designed.

15. Current Roadmap

This is where the handoff changes dramatically.

Old roadmap:

Scheduler

Dashboard

Health

History

Delete all of that.

New roadmap:

Freeze frontend architecture

↓

Wireframes

↓

Interaction specification

↓

Component hierarchy

↓

Frontend implementation

↓

Only adjust backend if real UI friction appears

↓

Future:

Alerts

Forecasting

Risk Engine

Multiple providers

Authentication
16. Development Rules

Keep this.

But I'd add one new principle.

Every new feature should answer one question: Does this improve environmental understanding, or is it merely exposing more data?

That one sentence captures everything AeroC has become.
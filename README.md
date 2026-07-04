# AeroC V2

> A production-oriented environmental air quality data platform for automated collection, storage, and analytics.

## Overview

AeroC V2 is an end-to-end environmental monitoring platform designed to continuously collect air quality observations from external providers, store them in a normalized PostgreSQL database, and expose the data to analytics dashboards and downstream applications.

Unlike the original AeroC prototype, Version 2 separates data collection, persistence, business logic, and presentation into independent layers, allowing the platform to scale as additional monitoring locations, pollutants, and providers are introduced.

---

## Project Goals

* Build a reliable environmental data ingestion platform.
* Collect observations on a scheduled basis.
* Store historical measurements in a normalized relational database.
* Provide a stable backend for dashboards and analytics tools.
* Support future expansion to multiple providers and pollutants.

---

## Current Architecture

```text
                Scheduler
                    │
                    ▼
         Collection Service
                    │
                    ▼
         External Data Collectors
                    │
                    ▼
          Domain Transformation
                    │
                    ▼
            Repository Layer
                    │
                    ▼
              PostgreSQL
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
     REST API             BI / Dashboards
```

---

## Technology Stack

### Backend

* Python 3.13
* FastAPI
* SQLAlchemy 2.x
* Alembic

### Database

* PostgreSQL 18

### Planned Infrastructure

* APScheduler
* Docker (optional deployment)
* Streamlit / Power BI / Looker Studio

---

## Repository Structure

```text
backend/
│
├── alembic/
├── app/
│   ├── api/
│   ├── collectors/
│   ├── config/
│   ├── database/
│   ├── models/
│   ├── repositories/
│   ├── scheduler/
│   └── services/
│
├── scripts/
│   └── seed_data/
│
└── tests/

dashboard/
docs/
docker/
```

---

## Database Design

The platform follows a normalized schema.

* **cities** — monitored locations
* **observations** — collection events
* **observation_values** — pollutant measurements

This design supports multiple pollutants per observation without schema changes.

---

## Development Roadmap

### Milestone 1 — Platform Foundation ✅

* Project architecture
* PostgreSQL integration
* SQLAlchemy ORM
* Alembic migrations
* Normalized database schema
* Repository layer

### Milestone 2 — Data Ingestion (In Progress)

* Seed monitoring network
* Repository implementation
* Open-Meteo collector
* Collection service
* APScheduler integration

### Milestone 3 — API Layer

* Observation endpoints
* City endpoints
* Time-series queries
* Filtering

### Milestone 4 — Analytics

* Risk assessment services
* Historical trends
* Dashboard integration

---

## Development Principles

* Database-first architecture
* Repository pattern
* Separation of concerns
* Idempotent operational scripts
* Version-controlled schema
* Production-oriented design

---

## Project Status

Current Version:

**v0.1.0-alpha**

Status:

**Core platform foundation complete. Active development continues on the ingestion pipeline.**

---

## License

This project is licensed under the MIT License.

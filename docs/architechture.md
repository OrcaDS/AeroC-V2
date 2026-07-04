# AeroC V2 — Architecture Bible

> **Version:** 2.0.0 (Draft)
>
> **Status:** Living Document
>
> **Purpose:** This document defines the architectural vision, engineering principles, and system boundaries of AeroC V2. Every design decision should align with this document.

---

# 1. Mission

AeroC is an environmental data platform that continuously collects, stores, and serves air quality observations through a reliable and maintainable backend architecture.

The platform is designed as if it were an internal system used by an environmental agency responsible for monitoring air quality over long periods of time.

The emphasis is not on visualization.

The emphasis is on trustworthy data.

---

# 2. Core Philosophy

AeroC is **not** a dashboard.

AeroC is **not** a FastAPI project.

AeroC is **a data platform.**

Everything else exists to support the lifecycle of environmental data.

```
Collect

↓

Validate

↓

Store

↓

Serve

↓

Visualize
```

Data is the product.

---

# 3. System Principles

## Principle 1 — Database is the Source of Truth

Once a measurement has been successfully collected and validated, PostgreSQL becomes the authoritative source.

No dashboard should directly consume external APIs.

No API endpoint should depend on live third-party responses.

---

## Principle 2 — Separation of Responsibilities

Every component should have one clearly defined responsibility.

| Component  | Responsibility                             |
| ---------- | ------------------------------------------ |
| Collectors | Retrieve external environmental data       |
| Validators | Ensure incoming data is correct and usable |
| Database   | Persist validated information              |
| Services   | Execute business logic                     |
| API        | Expose data to clients                     |
| Dashboard  | Present information to users               |

---

## Principle 3 — Automation First

Data collection must happen automatically.

Users should never trigger data ingestion.

The scheduler owns data collection.

---

## Principle 4 — Historical Data Matters

Measurements are never overwritten.

Each observation represents a point in time.

Historical trends are first-class citizens.

---

## Principle 5 — Configuration Over Hardcoding

Infrastructure values must live in configuration.

Examples include:

* database credentials
* API endpoints
* scheduler intervals
* environment variables

Application code should not contain environment-specific values.

---

# 4. High-Level Architecture

```
               Open-Meteo API
                      │
                      ▼
               Data Collector
                      │
                      ▼
               Data Validation
                      │
                      ▼
                 PostgreSQL
              (Source of Truth)
                 ▲          ▲
                 │          │
          FastAPI API   Scheduler
                 │
                 ▼
          Dashboard / BI Tools
```

---

# 5. Project Structure

```
backend/

app/

├── api/
├── collectors/
├── config/
├── database/
├── models/
├── repositories/
├── scheduler/
├── services/
└── main.py
```

Folder responsibilities:

### api/

HTTP endpoints.

No business logic.

---

### collectors/

Responsible for communicating with external providers.

Examples:

* Open-Meteo
* Future government APIs

Collectors never write directly to the database.

---

### config/

Application configuration.

Responsible for loading environment variables.

---

### database/

Infrastructure layer.

Responsible for:

* SQLAlchemy engine
* sessions
* migrations

---

### models/

Domain models representing the database schema.

Examples:

* City
* Measurement

---

### repositories/

Responsible for persistence.

Repositories perform database operations.

Services should never execute SQL directly.

---

### scheduler/

Runs automated collection jobs.

Owns all recurring tasks.

---

### services/

Business logic.

Examples:

* storing measurements
* validation workflows
* statistics
* aggregation

---

# 6. Data Flow

```
Scheduler

↓

Collector

↓

Validation

↓

Repository

↓

PostgreSQL

↓

API

↓

Dashboard
```

The flow is intentionally one-directional.

---

# 7. Database Philosophy

The database is normalized.

Reference data and observations are separated.

Reference information changes rarely.

Measurements change continuously.

Initial entities:

* City
* Measurement

Reference data should not be duplicated across millions of observations.

---

# 8. Initial Scope (V2)

Included:

* PM2.5 collection
* Scheduled ingestion
* PostgreSQL storage
* Historical measurements
* REST API
* Dashboard integration

Not included:

* Machine Learning
* Prediction models
* User authentication
* Alert notifications
* Multiple pollutants
* Multiple data providers

These belong to future versions.

---

# 9. Engineering Standards

## Single Responsibility

Each module should do one thing well.

---

## Explicit Naming

Avoid abbreviations unless universally accepted.

Prefer:

```
measurement_repository.py
```

instead of

```
repo.py
```

---

## Small Functions

Functions should have one responsibility.

Prefer composition over long functions.

---

## Readability First

Code is written for humans before computers.

Clarity is preferred over cleverness.

---

## No Magic Values

Constants belong in configuration or clearly named constants.

---

# 10. Future Expansion

The architecture should support future additions without major redesign.

Potential future modules include:

* PM10
* NO₂
* CO
* O₃
* AQI computation
* Weather enrichment
* Multiple countries
* GIS integration
* Alert engine
* Machine learning forecasts
* Data quality scoring

The current architecture should make these additions evolutionary rather than disruptive.

---

# 11. Current Technology Stack

| Layer         | Technology        |
| ------------- | ----------------- |
| Language      | Python 3.13       |
| Backend       | FastAPI           |
| Database      | PostgreSQL 18     |
| ORM           | SQLAlchemy        |
| Migrations    | Alembic           |
| Scheduler     | APScheduler       |
| Configuration | Pydantic Settings |
| HTTP Client   | HTTPX             |

---

# 12. Definition of Done

A feature is considered complete when:

* it satisfies its functional requirements;
* it follows the project architecture;
* it includes appropriate validation;
* it does not introduce unnecessary coupling;
* it can be extended without significant redesign.

Working code alone is not considered complete.

---

# 13. Long-Term Vision

AeroC should evolve into a modular environmental monitoring platform capable of supporting multiple pollutants, multiple data providers, and multiple visualization tools while maintaining a clean separation between data ingestion, storage, business logic, and presentation.

The goal is to build a platform that is reliable, maintainable, and extensible—not simply an application that works.

from __future__ import annotations

import logging
from datetime import datetime, timezone

import psycopg
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["operations"], include_in_schema=False)


def database_health_check() -> tuple[bool, str | None]:
    """Run a short, independent PostgreSQL readiness probe."""
    connect_kwargs: dict[str, object] = {
        "host": settings.DATABASE_HOST,
        "port": settings.DATABASE_PORT,
        "dbname": settings.DATABASE_NAME,
        "user": settings.DATABASE_USER,
        "password": settings.DATABASE_PASSWORD.get_secret_value(),
        "connect_timeout": settings.HEALTH_DATABASE_TIMEOUT_SECONDS,
        "application_name": f"{settings.DATABASE_APPLICATION_NAME}-health",
        "sslmode": settings.DATABASE_SSLMODE,
        "options": f"-c statement_timeout={settings.HEALTH_DATABASE_TIMEOUT_SECONDS * 1000}",
    }
    if settings.DATABASE_SSLROOTCERT is not None:
        connect_kwargs["sslrootcert"] = str(settings.DATABASE_SSLROOTCERT)

    try:
        with psycopg.connect(**connect_kwargs) as connection:
            connection.execute("SELECT 1")
        return True, None
    except Exception as exc:
        error_type = type(exc).__name__
        logger.warning(
            "event=database_health_check_failed error_type=%s",
            error_type,
            extra={
                "event": "database_health_check_failed",
                "error_type": error_type,
            },
        )
        return False, error_type


def scheduler_status(request: Request) -> dict[str, object]:
    role = getattr(request.app.state, "process_role", settings.AEROC_PROCESS_ROLE)
    if role == "api":
        return {
            "enabled": False,
            "healthy": True,
            "running": False,
            "role": role,
        }

    scheduler = getattr(request.app.state, "collection_scheduler", None)
    if scheduler is None:
        return {
            "enabled": True,
            "healthy": False,
            "running": False,
            "role": role,
            "startup_error": "scheduler_not_available",
        }

    status = scheduler.status()
    status["role"] = role
    status["collection_fresh"] = collection_is_fresh(status)
    return status


def collection_is_fresh(status: dict[str, object]) -> bool:
    now = datetime.now(timezone.utc)
    last_run = status.get("last_run")
    if isinstance(last_run, dict):
        if last_run.get("status") not in {"succeeded", "partial"}:
            return False
        started_at = _parse_datetime(last_run.get("started_at"))
        if started_at is None:
            return False
        age_minutes = (now - started_at).total_seconds() / 60
        return age_minutes <= settings.COLLECTION_STALE_AFTER_MINUTES

    started_at = _parse_datetime(status.get("started_at"))
    if started_at is None:
        return False
    age_seconds = (now - started_at).total_seconds()
    return age_seconds <= settings.COLLECTION_STARTUP_GRACE_SECONDS


@router.get("/health/live")
def liveness(request: Request):
    return {
        "status": "alive",
        "environment": settings.AEROC_ENV,
        "instance_id": settings.AEROC_INSTANCE_ID,
        "role": getattr(request.app.state, "process_role", settings.AEROC_PROCESS_ROLE),
    }


@router.get("/health/ready")
def readiness(request: Request):
    database_healthy, database_error = database_health_check()
    scheduler = scheduler_status(request)
    role = scheduler["role"]
    scheduler_healthy = True
    if role == "api_scheduler":
        scheduler_healthy = bool(scheduler.get("healthy")) and bool(
            scheduler.get("collection_fresh")
        )

    ready = database_healthy and scheduler_healthy
    payload = {
        "status": "ready" if ready else "not_ready",
        "role": role,
        "database": {
            "healthy": database_healthy,
            "error_type": database_error,
        },
        "scheduler": scheduler,
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)


@router.get("/ops/status")
def operational_status(request: Request):
    database_healthy, database_error = database_health_check()
    return {
        "environment": settings.AEROC_ENV,
        "instance_id": settings.AEROC_INSTANCE_ID,
        "role": getattr(request.app.state, "process_role", settings.AEROC_PROCESS_ROLE),
        "database": {
            "healthy": database_healthy,
            "error_type": database_error,
        },
        "scheduler": scheduler_status(request),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed

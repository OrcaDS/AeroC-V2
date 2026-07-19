from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.ingestion.collectors.open_meteo import (
    CollectionCancelledError,
    OpenMeteoCollector,
)
from app.repositories.city_repository import CityRepository
from app.repositories.observation_repository import ObservationRepository
from app.services.collection_service import CollectionService

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class CollectionRunResult:
    run_id: str
    started_at: datetime
    duration_ms: int
    succeeded_cities: int = 0
    failed_cities: int = 0
    duplicate_cities: int = 0
    cancelled: bool = False

    @property
    def status(self) -> str:
        if self.cancelled:
            return "cancelled"
        if self.failed_cities and self.succeeded_cities:
            return "partial"
        if self.failed_cities:
            return "failed"
        return "succeeded"


class CollectionRunner:
    """Executes one collection cycle with an independent transaction per city."""

    def __init__(
        self,
        session_factory=SessionLocal,
        cancellation_event: Event | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.cancellation_event = cancellation_event or Event()

    def request_cancel(self) -> None:
        self.cancellation_event.set()

    def run_once(self) -> CollectionRunResult:
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        started_monotonic = time.perf_counter()

        logger.info(
            "event=collection_cycle_started run_id=%s started_at=%s",
            run_id,
            started_at.isoformat(),
            extra={
                "event": "collection_cycle_started",
                "run_id": run_id,
                "started_at": started_at.isoformat(),
            },
        )

        try:
            cities = self._load_active_cities()
        except Exception:
            duration_ms = self._duration_ms(started_monotonic)
            logger.exception(
                "event=collection_cycle_failed run_id=%s duration_ms=%s phase=load_cities",
                run_id,
                duration_ms,
                extra={
                    "event": "collection_cycle_failed",
                    "run_id": run_id,
                    "duration_ms": duration_ms,
                    "phase": "load_cities",
                },
            )
            raise

        succeeded_cities = 0
        failed_cities = 0
        duplicate_cities = 0
        cancelled = False

        for city in cities:
            if self.cancellation_event.is_set():
                cancelled = True
                break

            session: Session | None = None
            try:
                session = self.session_factory()
                service = self._build_service(session, run_id)
                created = service.collect_city(city)
                session.commit()
                succeeded_cities += 1
                if not created:
                    duplicate_cities += 1
            except CollectionCancelledError:
                cancelled = True
                self._safe_rollback(session, run_id, city.id)
                break
            except Exception as exc:
                failed_cities += 1
                self._safe_rollback(session, run_id, city.id)
                logger.exception(
                    "event=city_collection_failed run_id=%s city_id=%s city_name=%s error_type=%s",
                    run_id,
                    city.id,
                    city.name,
                    type(exc).__name__,
                    extra={
                        "event": "city_collection_failed",
                        "run_id": run_id,
                        "city_id": city.id,
                        "city_name": city.name,
                        "error_type": type(exc).__name__,
                    },
                )
            finally:
                self._safe_close(session, run_id, city.id)

        result = CollectionRunResult(
            run_id=run_id,
            started_at=started_at,
            duration_ms=self._duration_ms(started_monotonic),
            succeeded_cities=succeeded_cities,
            failed_cities=failed_cities,
            duplicate_cities=duplicate_cities,
            cancelled=cancelled,
        )

        log_method = logger.info if result.status == "succeeded" else logger.warning
        log_method(
            "event=collection_cycle_%s run_id=%s duration_ms=%s succeeded_cities=%s failed_cities=%s duplicate_cities=%s",
            result.status,
            result.run_id,
            result.duration_ms,
            result.succeeded_cities,
            result.failed_cities,
            result.duplicate_cities,
            extra={
                "event": f"collection_cycle_{result.status}",
                "run_id": result.run_id,
                "duration_ms": result.duration_ms,
                "succeeded_cities": result.succeeded_cities,
                "failed_cities": result.failed_cities,
                "duplicate_cities": result.duplicate_cities,
            },
        )
        return result

    def _load_active_cities(self) -> list:
        session: Session | None = None
        try:
            session = self.session_factory()
            return CityRepository(session).get_active()
        finally:
            self._safe_close(session, run_id=None, city_id=None)

    def _build_service(
        self,
        session: Session,
        run_id: str,
    ) -> CollectionService:
        return CollectionService(
            observation_repository=ObservationRepository(session),
            collector=OpenMeteoCollector(cancellation_event=self.cancellation_event),
            run_id=run_id,
        )

    @staticmethod
    def _safe_rollback(session: Session | None, run_id: str, city_id: int) -> None:
        if session is None:
            return
        try:
            session.rollback()
        except Exception:
            logger.exception(
                "event=city_rollback_failed run_id=%s city_id=%s",
                run_id,
                city_id,
            )

    @staticmethod
    def _safe_close(
        session: Session | None,
        run_id: str | None,
        city_id: int | None,
    ) -> None:
        if session is None:
            return
        try:
            session.close()
        except Exception:
            logger.exception(
                "event=database_session_close_failed run_id=%s city_id=%s",
                run_id,
                city_id,
            )

    @staticmethod
    def _duration_ms(started_monotonic: float) -> int:
        return int((time.perf_counter() - started_monotonic) * 1000)

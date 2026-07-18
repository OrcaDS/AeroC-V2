from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.ingestion.collectors.open_meteo import OpenMeteoCollector
from app.repositories.city_repository import CityRepository
from app.repositories.observation_repository import ObservationRepository
from app.services.collection_service import CollectionService

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class CollectionRunResult:
    run_id: str
    started_at: datetime
    duration_ms: int


class CollectionRunner:
    """Executes one collection cycle end to end."""

    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

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

        session: Session = self.session_factory()

        try:
            service = self._build_service(session, run_id)
            service.collect_all()
            session.commit()

            duration_ms = self._duration_ms(started_monotonic)
            logger.info(
                "event=collection_cycle_succeeded run_id=%s duration_ms=%s",
                run_id,
                duration_ms,
                extra={
                    "event": "collection_cycle_succeeded",
                    "run_id": run_id,
                    "duration_ms": duration_ms,
                },
            )
            return CollectionRunResult(
                run_id=run_id,
                started_at=started_at,
                duration_ms=duration_ms,
            )
        except Exception:
            session.rollback()
            duration_ms = self._duration_ms(started_monotonic)
            logger.exception(
                "event=collection_cycle_failed run_id=%s duration_ms=%s",
                run_id,
                duration_ms,
                extra={
                    "event": "collection_cycle_failed",
                    "run_id": run_id,
                    "duration_ms": duration_ms,
                },
            )
            raise
        finally:
            session.close()

    def _build_service(
        self,
        session: Session,
        run_id: str,
    ) -> CollectionService:
        city_repository = CityRepository(session)
        observation_repository = ObservationRepository(session)
        collector = OpenMeteoCollector()

        return CollectionService(
            city_repository=city_repository,
            observation_repository=observation_repository,
            collector=collector,
            run_id=run_id,
        )

    @staticmethod
    def _duration_ms(started_monotonic: float) -> int:
        return int((time.perf_counter() - started_monotonic) * 1000)

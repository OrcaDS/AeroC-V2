from __future__ import annotations

import logging
from datetime import timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.runtime.collection_runner import CollectionRunner

logger = logging.getLogger(__name__)

COLLECTION_JOB_ID = "collection_cycle"


class CollectionScheduler:
    """
    Schedules recurring collection for a single-process AeroC backend.

    This assumes exactly one application process owns the scheduler.
    """

    def __init__(
        self,
        runner: CollectionRunner,
        interval_minutes: int,
    ) -> None:
        self.runner = runner
        self.interval_minutes = interval_minutes
        self.scheduler = BackgroundScheduler(timezone=timezone.utc)

    def start(self) -> None:
        self.scheduler.add_job(
            self._run_collection_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id=COLLECTION_JOB_ID,
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        self.scheduler.start()

        logger.info(
            "event=scheduler_started job_id=%s interval_minutes=%s next_run_at=%s",
            COLLECTION_JOB_ID,
            self.interval_minutes,
            self._next_run_at(),
            extra={
                "event": "scheduler_started",
                "job_id": COLLECTION_JOB_ID,
                "interval_minutes": self.interval_minutes,
                "next_run_at": self._next_run_at(),
            },
        )

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

    def _run_collection_job(self) -> None:
        try:
            result = self.runner.run_once()
            logger.info(
                "event=scheduled_collection_completed run_id=%s duration_ms=%s next_run_at=%s",
                result.run_id,
                result.duration_ms,
                self._next_run_at(),
                extra={
                    "event": "scheduled_collection_completed",
                    "run_id": result.run_id,
                    "duration_ms": result.duration_ms,
                    "next_run_at": self._next_run_at(),
                },
            )
        except Exception as exc:
            logger.error(
                "event=scheduled_collection_failed error_type=%s error_message=%s next_run_at=%s",
                type(exc).__name__,
                str(exc),
                self._next_run_at(),
                extra={
                    "event": "scheduled_collection_failed",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "next_run_at": self._next_run_at(),
                },
            )

    def _next_run_at(self) -> str | None:
        job = self.scheduler.get_job(COLLECTION_JOB_ID)
        next_run_time = None if job is None else getattr(job, "next_run_time", None)
        if next_run_time is None:
            return None
        return next_run_time.isoformat()

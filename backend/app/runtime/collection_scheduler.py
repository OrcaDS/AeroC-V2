from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import Event, Lock

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_MISSED,
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.runtime.collection_runner import CollectionRunResult, CollectionRunner

logger = logging.getLogger(__name__)

COLLECTION_JOB_ID = "collection_cycle"


class CollectionScheduler:
    """Own the single recurring collection job for one application process."""

    def __init__(
        self,
        runner: CollectionRunner,
        interval_minutes: int,
        *,
        run_on_startup: bool = True,
        misfire_grace_seconds: int = 300,
        shutdown_grace_seconds: int = 90,
        instance_id: str = "unknown",
    ) -> None:
        self.runner = runner
        self.interval_minutes = interval_minutes
        self.run_on_startup = run_on_startup
        self.misfire_grace_seconds = misfire_grace_seconds
        self.shutdown_grace_seconds = shutdown_grace_seconds
        self.instance_id = instance_id
        self.scheduler = BackgroundScheduler(timezone=timezone.utc)
        self._state_lock = Lock()
        self._job_idle = Event()
        self._job_idle.set()
        self._started_at: datetime | None = None
        self._shutting_down = False
        self._startup_error: str | None = None
        self._last_result: CollectionRunResult | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        try:
            self.scheduler.add_listener(
                self._handle_job_event,
                EVENT_JOB_EXECUTED
                | EVENT_JOB_ERROR
                | EVENT_JOB_MISSED
                | EVENT_JOB_MAX_INSTANCES,
            )
            job_options = {}
            if self.run_on_startup:
                job_options["next_run_time"] = datetime.now(timezone.utc)
            self.scheduler.add_job(
                self._run_collection_job,
                trigger=IntervalTrigger(minutes=self.interval_minutes),
                id=COLLECTION_JOB_ID,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=self.misfire_grace_seconds,
                replace_existing=True,
                **job_options,
            )
            self.scheduler.start()
            with self._state_lock:
                self._started_at = datetime.now(timezone.utc)
                self._startup_error = None
        except Exception as exc:
            with self._state_lock:
                self._startup_error = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "event=scheduler_start_failed instance_id=%s job_id=%s",
                self.instance_id,
                COLLECTION_JOB_ID,
            )
            raise

        logger.info(
            "event=scheduler_started instance_id=%s job_id=%s interval_minutes=%s next_run_at=%s",
            self.instance_id,
            COLLECTION_JOB_ID,
            self.interval_minutes,
            self._next_run_at(),
            extra={
                "event": "scheduler_started",
                "instance_id": self.instance_id,
                "job_id": COLLECTION_JOB_ID,
                "interval_minutes": self.interval_minutes,
                "next_run_at": self._next_run_at(),
            },
        )

    def shutdown(self) -> bool:
        """Cooperatively stop work and wait no longer than the configured budget."""
        with self._state_lock:
            self._shutting_down = True

        self.runner.request_cancel()
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

        completed = self._job_idle.wait(timeout=self.shutdown_grace_seconds)
        if not completed:
            logger.error(
                "event=scheduler_shutdown_timed_out instance_id=%s grace_seconds=%s",
                self.instance_id,
                self.shutdown_grace_seconds,
            )
        else:
            logger.info(
                "event=scheduler_shutdown_completed instance_id=%s",
                self.instance_id,
            )
        return completed

    def status(self) -> dict[str, object]:
        with self._state_lock:
            last_result = self._last_result
            startup_error = self._startup_error
            last_error = self._last_error
            started_at = self._started_at
            shutting_down = self._shutting_down

        scheduler_thread = getattr(self.scheduler, "_thread", None)
        thread_alive = scheduler_thread is not None and scheduler_thread.is_alive()
        running = self.scheduler.running and thread_alive and not shutting_down
        return {
            "enabled": True,
            "healthy": running and startup_error is None,
            "running": running,
            "thread_alive": thread_alive,
            "shutting_down": shutting_down,
            "instance_id": self.instance_id,
            "job_id": COLLECTION_JOB_ID,
            "started_at": self._isoformat(started_at),
            "next_run_at": self._next_run_at(),
            "startup_error": startup_error,
            "last_error": last_error,
            "last_run": None if last_result is None else {
                "run_id": last_result.run_id,
                "status": last_result.status,
                "started_at": last_result.started_at.isoformat(),
                "duration_ms": last_result.duration_ms,
                "succeeded_cities": last_result.succeeded_cities,
                "failed_cities": last_result.failed_cities,
                "duplicate_cities": last_result.duplicate_cities,
            },
        }

    def _run_collection_job(self) -> CollectionRunResult:
        self._job_idle.clear()
        try:
            result = self.runner.run_once()
            with self._state_lock:
                self._last_result = result
                self._last_error = None if result.status == "succeeded" else result.status

            log_method = logger.info if result.status == "succeeded" else logger.warning
            log_method(
                "event=scheduled_collection_%s run_id=%s duration_ms=%s next_run_at=%s",
                result.status,
                result.run_id,
                result.duration_ms,
                self._next_run_at(),
                extra={
                    "event": f"scheduled_collection_{result.status}",
                    "run_id": result.run_id,
                    "duration_ms": result.duration_ms,
                    "next_run_at": self._next_run_at(),
                },
            )
            return result
        except Exception as exc:
            with self._state_lock:
                self._last_error = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "event=scheduled_collection_failed error_type=%s next_run_at=%s",
                type(exc).__name__,
                self._next_run_at(),
                extra={
                    "event": "scheduled_collection_failed",
                    "error_type": type(exc).__name__,
                    "next_run_at": self._next_run_at(),
                },
            )
            raise
        finally:
            self._job_idle.set()

    def _handle_job_event(self, event) -> None:
        if event.code == EVENT_JOB_MISSED:
            logger.warning(
                "event=scheduler_job_missed job_id=%s scheduled_run_time=%s",
                event.job_id,
                self._isoformat(getattr(event, "scheduled_run_time", None)),
            )
        elif event.code == EVENT_JOB_MAX_INSTANCES:
            logger.warning(
                "event=scheduler_job_overlap_skipped job_id=%s",
                event.job_id,
            )
        elif event.code == EVENT_JOB_ERROR:
            logger.error(
                "event=scheduler_job_error job_id=%s error_type=%s",
                event.job_id,
                type(event.exception).__name__,
            )
        elif event.code == EVENT_JOB_EXECUTED:
            logger.debug("event=scheduler_job_executed job_id=%s", event.job_id)

    def _next_run_at(self) -> str | None:
        job = self.scheduler.get_job(COLLECTION_JOB_ID)
        next_run_time = None if job is None else getattr(job, "next_run_time", None)
        return self._isoformat(next_run_time)

    @staticmethod
    def _isoformat(value: datetime | None) -> str | None:
        return None if value is None else value.isoformat()

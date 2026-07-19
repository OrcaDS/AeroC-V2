from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import Event

import pytest

from app.runtime.collection_scheduler import COLLECTION_JOB_ID, CollectionScheduler
from app.runtime.collection_runner import CollectionRunResult


class FakeRunner:
    def __init__(
        self,
        should_fail: bool = False,
        block: bool = False,
        ignore_cancel: bool = False,
    ) -> None:
        self.should_fail = should_fail
        self.block = block
        self.ignore_cancel = ignore_cancel
        self.calls = 0
        self.cancelled = Event()
        self.started = Event()

    def run_once(self) -> CollectionRunResult:
        self.calls += 1
        self.started.set()
        if self.block:
            if self.ignore_cancel:
                time.sleep(0.2)
            else:
                self.cancelled.wait(timeout=2)
        if self.should_fail:
            raise RuntimeError("failure")
        return CollectionRunResult(
            run_id="run-123",
            started_at=datetime.now(timezone.utc),
            duration_ms=42,
        )

    def request_cancel(self) -> None:
        self.cancelled.set()


def test_scheduler_job_logs_success(caplog) -> None:
    scheduler = CollectionScheduler(
        runner=FakeRunner(),
        interval_minutes=5,
        run_on_startup=False,
    )
    caplog.set_level(logging.INFO)
    scheduler.scheduler.add_job(
        scheduler._run_collection_job,
        id=COLLECTION_JOB_ID,
        replace_existing=True,
    )

    scheduler._run_collection_job()

    assert "event=scheduled_collection_succeeded" in caplog.text


def test_scheduler_job_reraises_for_apscheduler_diagnostics(caplog) -> None:
    scheduler = CollectionScheduler(
        runner=FakeRunner(should_fail=True),
        interval_minutes=5,
        run_on_startup=False,
    )
    caplog.set_level(logging.INFO)
    scheduler.scheduler.add_job(
        scheduler._run_collection_job,
        id=COLLECTION_JOB_ID,
        replace_existing=True,
    )

    with pytest.raises(RuntimeError, match="failure"):
        scheduler._run_collection_job()

    assert "event=scheduled_collection_failed" in caplog.text


def test_startup_collection_uses_the_recurring_apscheduler_job() -> None:
    runner = FakeRunner()
    scheduler = CollectionScheduler(
        runner=runner,
        interval_minutes=60,
        run_on_startup=True,
        shutdown_grace_seconds=1,
    )

    scheduler.start()
    assert runner.started.wait(timeout=1)
    job = scheduler.scheduler.get_job(COLLECTION_JOB_ID)

    assert job is not None
    assert job.max_instances == 1
    assert job.coalesce is True
    assert runner.calls == 1
    assert scheduler.shutdown() is True


def test_shutdown_signals_cancellation_and_respects_budget() -> None:
    runner = FakeRunner(block=True)
    scheduler = CollectionScheduler(
        runner=runner,
        interval_minutes=60,
        run_on_startup=True,
        shutdown_grace_seconds=1,
    )
    scheduler.start()
    assert runner.started.wait(timeout=1)

    started = time.perf_counter()
    completed = scheduler.shutdown()
    elapsed = time.perf_counter() - started

    assert completed is True
    assert runner.cancelled.is_set()
    assert elapsed < 1


def test_shutdown_returns_when_cooperative_work_exceeds_budget(caplog) -> None:
    runner = FakeRunner(block=True, ignore_cancel=True)
    scheduler = CollectionScheduler(
        runner=runner,
        interval_minutes=60,
        run_on_startup=True,
        shutdown_grace_seconds=0.05,
    )
    caplog.set_level(logging.ERROR)
    scheduler.start()
    assert runner.started.wait(timeout=1)

    started = time.perf_counter()
    completed = scheduler.shutdown()
    elapsed = time.perf_counter() - started

    assert completed is False
    assert elapsed < 0.15
    assert "event=scheduler_shutdown_timed_out" in caplog.text

from __future__ import annotations

import logging

from app.runtime.collection_scheduler import CollectionScheduler
from app.runtime.collection_runner import CollectionRunResult


class FakeRunner:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls = 0

    def run_once(self) -> CollectionRunResult:
        self.calls += 1
        if self.should_fail:
            raise RuntimeError("failure")
        return CollectionRunResult(
            run_id="run-123",
            started_at=None,
            duration_ms=42,
        )


def test_scheduler_job_logs_success_and_continues(caplog) -> None:
    scheduler = CollectionScheduler(runner=FakeRunner(), interval_minutes=5)
    caplog.set_level(logging.INFO)

    scheduler.scheduler.add_job(
        scheduler._run_collection_job,
        id="collection_cycle",
        replace_existing=True,
    )
    scheduler._run_collection_job()

    assert "event=scheduled_collection_completed" in caplog.text


def test_scheduler_job_logs_failure_without_raising(caplog) -> None:
    scheduler = CollectionScheduler(runner=FakeRunner(should_fail=True), interval_minutes=5)
    caplog.set_level(logging.INFO)

    scheduler.scheduler.add_job(
        scheduler._run_collection_job,
        id="collection_cycle",
        replace_existing=True,
    )
    scheduler._run_collection_job()

    assert "event=scheduled_collection_failed" in caplog.text

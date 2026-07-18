from __future__ import annotations

import logging
from datetime import datetime, timezone

import pytest

from app.runtime.collection_runner import CollectionRunner


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class FakeService:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.called = False

    def collect_all(self) -> None:
        self.called = True
        if self.should_fail:
            raise RuntimeError("boom")


def test_collection_runner_commits_and_closes_session(caplog: pytest.LogCaptureFixture) -> None:
    session = FakeSession()
    service = FakeService()
    caplog.set_level(logging.INFO)

    class TestRunner(CollectionRunner):
        def _build_service(self, current_session, run_id: str):
            assert current_session is session
            assert run_id
            return service

    runner = TestRunner(session_factory=lambda: session)

    result = runner.run_once()

    assert service.called is True
    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True
    assert result.run_id
    assert result.started_at <= datetime.now(timezone.utc)
    assert "event=collection_cycle_started" in caplog.text
    assert "event=collection_cycle_succeeded" in caplog.text


def test_collection_runner_rolls_back_and_reraises(caplog: pytest.LogCaptureFixture) -> None:
    session = FakeSession()
    service = FakeService(should_fail=True)
    caplog.set_level(logging.INFO)

    class TestRunner(CollectionRunner):
        def _build_service(self, current_session, run_id: str):
            assert current_session is session
            assert run_id
            return service

    runner = TestRunner(session_factory=lambda: session)

    with pytest.raises(RuntimeError, match="boom"):
        runner.run_once()

    assert service.called is True
    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True
    assert "event=collection_cycle_failed" in caplog.text

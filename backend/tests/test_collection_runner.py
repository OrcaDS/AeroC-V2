from __future__ import annotations

import logging
from types import SimpleNamespace

from app.ingestion.collectors.open_meteo import CollectionCancelledError
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
    def __init__(self, outcome: bool | Exception = True) -> None:
        self.outcome = outcome

    def collect_city(self, city) -> bool:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class TestRunner(CollectionRunner):
    __test__ = False

    def __init__(self, cities, services, sessions):
        super().__init__(session_factory=lambda: sessions.pop(0))
        self.cities = cities
        self.services = services

    def _load_active_cities(self):
        return self.cities

    def _build_service(self, current_session, run_id: str):
        assert run_id
        return self.services.pop(0)


def test_collection_runner_uses_independent_city_transactions(caplog) -> None:
    cities = [
        SimpleNamespace(id=1, name="Manila"),
        SimpleNamespace(id=2, name="Quezon City"),
        SimpleNamespace(id=3, name="Makati"),
    ]
    sessions = [FakeSession(), FakeSession(), FakeSession()]
    retained_sessions = list(sessions)
    services = [FakeService(True), FakeService(RuntimeError("boom")), FakeService(False)]
    caplog.set_level(logging.INFO)

    result = TestRunner(cities, services, sessions).run_once()

    assert result.status == "partial"
    assert result.succeeded_cities == 2
    assert result.failed_cities == 1
    assert result.duplicate_cities == 1
    assert retained_sessions[0].committed is True
    assert retained_sessions[1].rolled_back is True
    assert retained_sessions[2].committed is True
    assert all(session.closed for session in retained_sessions)
    assert "event=city_collection_failed" in caplog.text
    assert "event=collection_cycle_partial" in caplog.text


def test_collection_runner_stops_cooperatively_on_cancellation() -> None:
    cities = [
        SimpleNamespace(id=1, name="Manila"),
        SimpleNamespace(id=2, name="Quezon City"),
    ]
    sessions = [FakeSession(), FakeSession()]
    retained_sessions = list(sessions)
    services = [
        FakeService(CollectionCancelledError("shutdown")),
        FakeService(True),
    ]

    result = TestRunner(cities, services, sessions).run_once()

    assert result.status == "cancelled"
    assert result.cancelled is True
    assert retained_sessions[0].rolled_back is True
    assert retained_sessions[0].closed is True
    assert retained_sessions[1].closed is False

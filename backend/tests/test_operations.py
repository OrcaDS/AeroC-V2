from datetime import datetime, timezone

from app.api import ops


class FakeScheduler:
    def __init__(self, healthy: bool = True, last_status: str = "succeeded") -> None:
        self.healthy = healthy
        self.last_status = last_status

    def status(self):
        return {
            "enabled": True,
            "healthy": self.healthy,
            "running": self.healthy,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "next_run_at": datetime.now(timezone.utc).isoformat(),
            "last_run": {
                "run_id": "run-123",
                "status": self.last_status,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": 42,
                "succeeded_cities": 8,
                "failed_cities": 0,
                "duplicate_cities": 0,
            },
        }


def test_liveness_has_no_database_dependency(client, monkeypatch):
    monkeypatch.setattr(
        ops,
        "database_health_check",
        lambda: (_ for _ in ()).throw(AssertionError("database probe called")),
    )

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_api_role_is_ready_without_scheduler(client, monkeypatch):
    monkeypatch.setattr(ops, "database_health_check", lambda: (True, None))
    client.app.state.process_role = "api"

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["scheduler"]["enabled"] is False


def test_api_scheduler_is_not_ready_when_scheduler_is_missing(client, monkeypatch):
    monkeypatch.setattr(ops, "database_health_check", lambda: (True, None))
    client.app.state.process_role = "api_scheduler"
    if hasattr(client.app.state, "collection_scheduler"):
        del client.app.state.collection_scheduler

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["scheduler"]["healthy"] is False


def test_api_scheduler_readiness_requires_healthy_fresh_collection(client, monkeypatch):
    monkeypatch.setattr(ops, "database_health_check", lambda: (True, None))
    client.app.state.process_role = "api_scheduler"
    client.app.state.collection_scheduler = FakeScheduler()

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["scheduler"]["collection_fresh"] is True


def test_database_outage_fails_readiness_without_exposing_error_message(client, monkeypatch):
    monkeypatch.setattr(ops, "database_health_check", lambda: (False, "OperationalError"))
    client.app.state.process_role = "api"

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["database"] == {
        "healthy": False,
        "error_type": "OperationalError",
    }

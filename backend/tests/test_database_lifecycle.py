from app.database import session as database_session


def test_engine_uses_stale_connection_protection():
    assert database_session.engine.pool._pre_ping is True


def test_dispose_engine_closes_pool(monkeypatch):
    calls = []

    monkeypatch.setattr(
        database_session.engine,
        "dispose",
        lambda *, close: calls.append(close),
    )

    database_session.dispose_engine()

    assert calls == [True]

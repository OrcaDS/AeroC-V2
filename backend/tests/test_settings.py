from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def build_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "API_TITLE": "AeroC API",
        "API_VERSION": "1.0.0",
        "DATABASE_HOST": "localhost",
        "DATABASE_PORT": 5432,
        "DATABASE_NAME": "aeroc",
        "DATABASE_USER": "aeroc",
        "DATABASE_PASSWORD": "safe-development-password",
    }
    values.update(overrides)
    return Settings(**values)


def test_database_url_escapes_password_without_logging_it():
    settings = build_settings(DATABASE_PASSWORD="pa:ss@word")

    assert settings.database_url.render_as_string(hide_password=False) == (
        "postgresql+psycopg://aeroc:pa%3Ass%40word@localhost:5432/aeroc"
    )

    assert "pa:ss@word" not in repr(settings)


def test_scheduler_role_is_authoritative():
    assert build_settings(AEROC_PROCESS_ROLE="api").scheduler_enabled is False
    assert build_settings(AEROC_PROCESS_ROLE="api_scheduler").scheduler_enabled is True

    with pytest.raises(ValidationError, match="conflicts with AEROC_PROCESS_ROLE"):
        build_settings(AEROC_PROCESS_ROLE="api", SCHEDULER_ENABLED=True)

    with pytest.raises(ValidationError, match="exactly one web worker"):
        build_settings(AEROC_PROCESS_ROLE="api_scheduler", AEROC_WEB_WORKERS=2)


def test_production_requires_explicit_role_and_safe_credentials(monkeypatch):
    monkeypatch.delenv("AEROC_PROCESS_ROLE", raising=False)

    with pytest.raises(ValidationError, match="explicitly set"):
        build_settings(AEROC_ENV="production", DATABASE_SSLMODE="require")

    with pytest.raises(ValidationError, match="prohibited production placeholder"):
        build_settings(
            AEROC_ENV="production",
            AEROC_PROCESS_ROLE="api_scheduler",
            DATABASE_PASSWORD="changeme",
            DATABASE_SSLMODE="require",
        )


def test_certificate_verification_requires_readable_ca(tmp_path: Path):
    with pytest.raises(ValidationError, match="DATABASE_SSLROOTCERT is required"):
        build_settings(DATABASE_SSLMODE="verify-full")

    ca_file = tmp_path / "provider-ca.pem"
    ca_file.write_text("test-ca", encoding="utf-8")
    configured = build_settings(
        DATABASE_SSLMODE="verify-full",
        DATABASE_SSLROOTCERT=ca_file,
    )
    assert configured.database_connect_args["sslrootcert"] == str(ca_file)


def test_operational_bounds_are_validated():
    with pytest.raises(ValidationError):
        build_settings(COLLECTION_INTERVAL_MINUTES=0)

    with pytest.raises(ValidationError, match="must exceed"):
        build_settings(
            COLLECTION_INTERVAL_MINUTES=60,
            COLLECTION_STALE_AFTER_MINUTES=60,
        )

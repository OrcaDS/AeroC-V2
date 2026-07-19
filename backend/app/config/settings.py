from __future__ import annotations

import socket
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    # Runtime
    AEROC_ENV: Literal["development", "test", "production"] = "development"
    AEROC_PROCESS_ROLE: Literal["api", "api_scheduler"] = "api_scheduler"
    AEROC_INSTANCE_ID: str = Field(default_factory=socket.gethostname, min_length=1)
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["text", "json"] = "text"
    AEROC_WEB_WORKERS: int = Field(default=1, ge=1, le=32)
    SHUTDOWN_GRACE_SECONDS: int = Field(default=90, ge=1, le=600)

    # API
    API_TITLE: str = "AeroC API"
    API_VERSION: str = "1.0.0"

    # Database
    DATABASE_HOST: str
    DATABASE_PORT: int = Field(default=5432, ge=1, le=65535)
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: SecretStr
    DATABASE_SSLMODE: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"] = "prefer"
    DATABASE_SSLROOTCERT: Path | None = None
    DATABASE_CONNECT_TIMEOUT_SECONDS: int = Field(default=5, ge=1, le=60)
    DATABASE_POOL_SIZE: int = Field(default=5, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=5, ge=0, le=100)
    DATABASE_POOL_TIMEOUT_SECONDS: int = Field(default=10, ge=1, le=120)
    DATABASE_POOL_RECYCLE_SECONDS: int = Field(default=1800, ge=60, le=86400)
    DATABASE_STATEMENT_TIMEOUT_MS: int = Field(default=15000, ge=1000, le=300000)
    DATABASE_LOCK_TIMEOUT_MS: int = Field(default=5000, ge=100, le=300000)
    DATABASE_APPLICATION_NAME: str = Field(default="aeroc-local", min_length=1, max_length=63)
    HEALTH_DATABASE_TIMEOUT_SECONDS: int = Field(default=2, ge=1, le=30)

    # Scheduler and collection
    COLLECTION_INTERVAL_MINUTES: int = Field(default=60, ge=1, le=1440)
    COLLECTION_RUN_ON_STARTUP: bool = True
    SCHEDULER_MISFIRE_GRACE_SECONDS: int = Field(default=300, ge=1, le=86400)
    COLLECTION_STARTUP_GRACE_SECONDS: int = Field(default=120, ge=1, le=3600)
    COLLECTION_STALE_AFTER_MINUTES: int = Field(default=150, ge=2, le=4320)

    # Deprecated compatibility input. Process role is authoritative.
    SCHEDULER_ENABLED: bool | None = None

    # Provider resilience
    OPEN_METEO_BASE_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_TIMEOUT_SECONDS: float = Field(default=20.0, gt=0, le=120)
    OPEN_METEO_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=5)
    OPEN_METEO_RETRY_BASE_SECONDS: float = Field(default=1.0, ge=0, le=30)
    OPEN_METEO_RETRY_MAX_SECONDS: float = Field(default=8.0, ge=0, le=120)

    @property
    def scheduler_enabled(self) -> bool:
        return self.AEROC_PROCESS_ROLE == "api_scheduler"

    @property
    def database_url(self) -> URL:
        """Build the application database URL without string interpolation."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.DATABASE_USER,
            password=self.DATABASE_PASSWORD.get_secret_value(),
            host=self.DATABASE_HOST,
            port=self.DATABASE_PORT,
            database=self.DATABASE_NAME,
        )

    @property
    def database_connect_args(self) -> dict[str, object]:
        connect_args: dict[str, object] = {
            "connect_timeout": self.DATABASE_CONNECT_TIMEOUT_SECONDS,
            "application_name": self.DATABASE_APPLICATION_NAME,
            "sslmode": self.DATABASE_SSLMODE,
            "options": (
                f"-c statement_timeout={self.DATABASE_STATEMENT_TIMEOUT_MS} "
                f"-c lock_timeout={self.DATABASE_LOCK_TIMEOUT_MS}"
            ),
        }
        if self.DATABASE_SSLROOTCERT is not None:
            connect_args["sslrootcert"] = str(self.DATABASE_SSLROOTCERT)
        return connect_args

    @model_validator(mode="after")
    def validate_operational_policy(self) -> "Settings":
        if self.COLLECTION_STALE_AFTER_MINUTES <= self.COLLECTION_INTERVAL_MINUTES:
            raise ValueError("COLLECTION_STALE_AFTER_MINUTES must exceed COLLECTION_INTERVAL_MINUTES")

        if self.OPEN_METEO_RETRY_MAX_SECONDS < self.OPEN_METEO_RETRY_BASE_SECONDS:
            raise ValueError("OPEN_METEO_RETRY_MAX_SECONDS must be at least OPEN_METEO_RETRY_BASE_SECONDS")

        if self.SCHEDULER_ENABLED is not None and self.SCHEDULER_ENABLED != self.scheduler_enabled:
            raise ValueError("SCHEDULER_ENABLED conflicts with AEROC_PROCESS_ROLE")

        if self.AEROC_ENV == "production":
            if "AEROC_PROCESS_ROLE" not in self.model_fields_set:
                raise ValueError("AEROC_PROCESS_ROLE must be explicitly set in production")

            password = self.DATABASE_PASSWORD.get_secret_value().strip().lower()
            if password in {"", "changeme", "aeroc_password", "password"}:
                raise ValueError("DATABASE_PASSWORD contains a prohibited production placeholder")

            if self.DATABASE_SSLMODE not in {"require", "verify-ca", "verify-full"}:
                raise ValueError("production DATABASE_SSLMODE must encrypt database transport")

        if self.scheduler_enabled and self.AEROC_WEB_WORKERS != 1:
            raise ValueError("api_scheduler requires exactly one web worker")

        if self.DATABASE_SSLMODE in {"verify-ca", "verify-full"}:
            if self.DATABASE_SSLROOTCERT is None:
                raise ValueError("DATABASE_SSLROOTCERT is required for certificate verification")
            if not self.DATABASE_SSLROOTCERT.is_file():
                raise ValueError("DATABASE_SSLROOTCERT must reference a readable CA certificate")

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

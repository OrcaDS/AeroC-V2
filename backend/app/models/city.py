"""
Represents a monitored city within the AeroC monitoring network.

Cities are reference data used by the ingestion pipeline to determine
which locations should be monitored. They are relatively static and
should not store environmental observations.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.sql import func

from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class City(Base):
    __tablename__ = "cities"

    __table_args__ = (
    UniqueConstraint("code", name="uq_city_code"),
    UniqueConstraint("name", "country", name="uq_city_country"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
    String(50),
    nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    latitude: Mapped[float] = mapped_column(
        Numeric(9, 6),
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Numeric(9, 6),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    observations: Mapped[list["Observation"]] = relationship(
    "Observation",
    back_populates="city",
    cascade="all, delete-orphan",
    )
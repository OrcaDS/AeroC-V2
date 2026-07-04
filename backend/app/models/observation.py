"""
Represents a single environmental observation event.

An observation captures the metadata of one successful data collection
for a monitored city. Individual pollutant measurements are stored
separately in ObservationValue.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Observation(Base):
    __tablename__ = "observations"

    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "observed_at",
            "source",
            name="uq_city_observed_source",
        ),
)

    id: Mapped[int] = mapped_column(primary_key=True)

    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id"),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    city = relationship(
        "City",
        back_populates="observations",
    )

    values = relationship(
        "ObservationValue",
        back_populates="observation",
        cascade="all, delete-orphan",
    )
"""
Represents an individual pollutant measurement collected during an observation.

Each Observation may contain multiple ObservationValues, one for each
pollutant reported by the external provider.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class ObservationValue(Base):
    __tablename__ = "observation_values"

    __table_args__ = (
    CheckConstraint(
        "value >= 0",
        name="ck_observation_value_non_negative",
    ),
    UniqueConstraint(
        "observation_id",
        "pollutant",
        name="uq_observation_pollutant",
    ),
)
    

    id: Mapped[int] = mapped_column(primary_key=True)

    observation_id: Mapped[int] = mapped_column(
        ForeignKey("observations.id"),
        nullable=False,
    )

    pollutant: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    value: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    observation = relationship(
    "Observation",
    back_populates="values",
)
    
"""
Repository for City persistence operations.

Repositories encapsulate all database access for a specific aggregate,
keeping SQLAlchemy logic out of services and collectors.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.city import City


class CityRepository:
    """Provides persistence operations for monitored cities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_cities(self) -> list[City]:
        """
        Return all cities currently enabled for monitoring.

        Returns:
            List of active City objects ordered alphabetically.
        """

        statement = (
            select(City)
            .where(City.active.is_(True))
            .order_by(City.country, City.name)
        )

        return list(self.session.scalars(statement))

    def get_by_code(self, code: str) -> City | None:
        """
        Retrieve a city by its unique monitoring code.
        """

        statement = (
            select(City)
            .where(City.code == code)
        )

        return self.session.scalar(statement)

    def add(self, city: City) -> None:
        """
        Stage a new city for persistence.

        The transaction is not committed here.
        """

        self.session.add(city)
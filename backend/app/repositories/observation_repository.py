from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, selectinload

from app.models.observation import Observation
from app.models.observation_value import ObservationValue


class ObservationRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, observation: Observation) -> None:
        self.session.add(observation)

    def create_if_absent(self, observation: Observation) -> bool:
        """Persist the first captured snapshot for an observation key.

        An Open-Meteo value can be revised by a later provider model run, but
        AeroC v1 intentionally preserves its first successful capture for a
        city, valid time, and source. Duplicate attempts are therefore ignored.
        """
        insert = self._dialect_insert()
        statement = (
            insert(Observation)
            .values(
                city_id=observation.city_id,
                source=observation.source,
                observed_at=observation.observed_at,
            )
            .on_conflict_do_nothing(
                index_elements=("city_id", "observed_at", "source"),
            )
            .returning(Observation.id)
        )
        observation_id = self.session.scalar(statement)

        if observation_id is None:
            return False

        self.session.add_all(
            [
                ObservationValue(
                    observation_id=observation_id,
                    pollutant=value.pollutant,
                    value=value.value,
                    unit=value.unit,
                )
                for value in observation.values
            ]
        )
        return True

    def _dialect_insert(self):
        if self.session.bind is not None and self.session.bind.dialect.name == "sqlite":
            return sqlite_insert
        return postgresql_insert

    def get_latest_for_city(self, city_id: int) -> Observation | None:
        statement = (
            select(Observation)
            .options(selectinload(Observation.values))
            .where(Observation.city_id == city_id)
            .order_by(Observation.observed_at.desc())
        )

        return self.session.scalars(statement).first()

    def get_latest_for_city_ids(
        self,
        city_ids: list[int],
    ) -> list[Observation]:
        if not city_ids:
            return []

        observations: list[Observation] = []

        for city_id in city_ids:
            observation = self.get_latest_for_city(city_id)
            if observation is not None:
                observations.append(observation)

        return observations

    def get_for_city_between(
        self,
        city_id: int,
        start: datetime,
        end: datetime,
    ) -> list[Observation]:
        statement = (
            select(Observation)
            .options(selectinload(Observation.values))
            .where(Observation.city_id == city_id)
            .where(Observation.observed_at >= start)
            .where(Observation.observed_at <= end)
            .order_by(Observation.observed_at.asc())
        )

        return list(self.session.scalars(statement))

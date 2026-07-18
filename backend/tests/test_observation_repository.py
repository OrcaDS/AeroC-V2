from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models.observation import Observation
from app.models.observation_value import ObservationValue
from app.repositories.observation_repository import ObservationRepository


def _observation(city_id: int, pm25: float) -> Observation:
    return Observation(
        city_id=city_id,
        source="open-meteo",
        observed_at=datetime(2026, 7, 18, 12, tzinfo=UTC),
        values=[ObservationValue(pollutant="pm2_5", value=pm25, unit="ug/m3")],
    )


def test_create_if_absent_preserves_first_collected_snapshot(db_session, seeded_city):
    repository = ObservationRepository(db_session)

    assert repository.create_if_absent(_observation(seeded_city.id, 20.0)) is True
    db_session.commit()

    assert repository.create_if_absent(_observation(seeded_city.id, 45.0)) is False
    db_session.commit()

    observations = list(db_session.scalars(select(Observation)))
    assert len(observations) == 1
    assert float(observations[0].values[0].value) == 20.0
    assert db_session.scalar(select(func.count()).select_from(ObservationValue)) == 1


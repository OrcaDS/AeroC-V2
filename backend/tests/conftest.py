from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.config.settings import settings
from app.database.base import Base

# API tests do not own the production scheduler. Scheduler lifecycle has a
# dedicated test module and must never make live provider/database calls here.
settings.AEROC_PROCESS_ROLE = "api"

from app.main import app
from app.models.city import City
from app.models.observation import Observation
from app.models.observation_value import ObservationValue


SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def seeded_city(db_session: Session) -> City:
    city = City(
        code="MNL",
        timezone="Asia/Manila",
        name="Manila",
        country="Philippines",
        latitude=14.5995,
        longitude=120.9842,
        active=True,
    )
    db_session.add(city)
    db_session.commit()
    db_session.refresh(city)
    return city


@pytest.fixture
def city_with_observation(db_session: Session, seeded_city: City) -> City:
    observation = Observation(
        city_id=seeded_city.id,
        source="open-meteo",
        observed_at=datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc),
    )
    observation.values = [
        ObservationValue(pollutant="pm2_5", value=24.5, unit="ug/m3"),
        ObservationValue(pollutant="pm10", value=38.2, unit="ug/m3"),
    ]
    db_session.add(observation)
    db_session.commit()
    return seeded_city


@pytest.fixture
def city_with_history(db_session: Session, seeded_city: City) -> City:
    observations = [
        Observation(
            city_id=seeded_city.id,
            source="open-meteo",
            observed_at=datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc),
            values=[
                ObservationValue(pollutant="pm2_5", value=20.0, unit="ug/m3"),
                ObservationValue(pollutant="pm10", value=30.0, unit="ug/m3"),
            ],
        ),
        Observation(
            city_id=seeded_city.id,
            source="open-meteo",
            observed_at=datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc),
            values=[
                ObservationValue(pollutant="pm2_5", value=24.5, unit="ug/m3"),
                ObservationValue(pollutant="pm10", value=38.2, unit="ug/m3"),
            ],
        ),
    ]
    db_session.add_all(observations)
    db_session.commit()
    return seeded_city


@pytest.fixture
def dashboard_dataset(db_session: Session) -> dict[str, City]:
    manila = City(
        code="MNL",
        timezone="Asia/Manila",
        name="Manila",
        country="Philippines",
        latitude=14.5995,
        longitude=120.9842,
        active=True,
    )
    quezon_city = City(
        code="QC",
        timezone="Asia/Manila",
        name="Quezon City",
        country="Philippines",
        latitude=14.6760,
        longitude=121.0437,
        active=True,
    )
    cebu = City(
        code="CEB",
        timezone="Asia/Manila",
        name="Cebu City",
        country="Philippines",
        latitude=10.3157,
        longitude=123.8854,
        active=True,
    )
    db_session.add_all([manila, quezon_city, cebu])
    db_session.commit()
    db_session.refresh(manila)
    db_session.refresh(quezon_city)
    db_session.refresh(cebu)

    observations = [
        Observation(
            city_id=manila.id,
            source="open-meteo",
            observed_at=datetime(2026, 7, 16, 11, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 7, 16, 11, 5, tzinfo=timezone.utc),
            values=[
                ObservationValue(pollutant="pm2_5", value=25.0, unit="ug/m3"),
                ObservationValue(pollutant="pm10", value=40.0, unit="ug/m3"),
                ObservationValue(pollutant="ozone", value=130.0, unit="ug/m3"),
            ],
        ),
        Observation(
            city_id=quezon_city.id,
            source="open-meteo",
            observed_at=datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc),
            values=[
                ObservationValue(pollutant="pm2_5", value=35.0, unit="ug/m3"),
                ObservationValue(pollutant="pm10", value=30.0, unit="ug/m3"),
                ObservationValue(pollutant="ozone", value=150.0, unit="ug/m3"),
            ],
        ),
    ]
    db_session.add_all(observations)
    db_session.commit()

    return {
        "manila": manila,
        "quezon_city": quezon_city,
        "cebu": cebu,
    }


@pytest.fixture
def trend_dataset(db_session: Session) -> dict[str, City]:
    city = City(
        code="MNL",
        timezone="Asia/Manila",
        name="Manila",
        country="Philippines",
        latitude=14.5995,
        longitude=120.9842,
        active=True,
    )
    db_session.add(city)
    db_session.commit()
    db_session.refresh(city)

    observations = [
        Observation(
            city_id=city.id,
            source="open-meteo",
            observed_at=datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 7, 4, 12, 5, tzinfo=timezone.utc),
            values=[
                ObservationValue(pollutant="pm2_5", value=20.0, unit="ug/m3"),
                ObservationValue(pollutant="pm10", value=30.0, unit="ug/m3"),
            ],
        ),
        Observation(
            city_id=city.id,
            source="open-meteo",
            observed_at=datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 7, 8, 12, 5, tzinfo=timezone.utc),
            values=[
                ObservationValue(pollutant="pm2_5", value=25.0, unit="ug/m3"),
                ObservationValue(pollutant="pm10", value=33.0, unit="ug/m3"),
            ],
        ),
        Observation(
            city_id=city.id,
            source="open-meteo",
            observed_at=datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 7, 12, 12, 5, tzinfo=timezone.utc),
            values=[
                ObservationValue(pollutant="pm2_5", value=30.0, unit="ug/m3"),
                ObservationValue(pollutant="pm10", value=32.0, unit="ug/m3"),
            ],
        ),
        Observation(
            city_id=city.id,
            source="open-meteo",
            observed_at=datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc),
            values=[
                ObservationValue(pollutant="pm2_5", value=40.0, unit="ug/m3"),
                ObservationValue(pollutant="pm10", value=34.0, unit="ug/m3"),
            ],
        ),
    ]
    db_session.add_all(observations)
    db_session.commit()

    return {"city": city}

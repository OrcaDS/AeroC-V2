from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models.observation import Observation
from app.repositories.city_repository import CityRepository
from app.schemas.observation import LatestObservationOut, ObservationOut, PollutantValueOut
from app.services.aqi_calculators import EpaUsAqiCalculator
from app.services.aqi_service import AqiService

router = APIRouter(tags=["observations"])


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


@router.get("/cities/{city_id}/observations/latest", response_model=ObservationOut)
def get_latest_observation(city_id: int, db: Session = Depends(get_db)):

    obs = (
        db.query(Observation)
        .filter(Observation.city_id == city_id)
        .order_by(Observation.observed_at.desc())
        .first()
    )

    if not obs:
        raise HTTPException(status_code=404, detail="No observations found")

    return obs


@router.get("/cities/{city_id}/latest", response_model=LatestObservationOut)
def get_latest_city_observation(city_id: int, db: Session = Depends(get_db)):
    city_repo = CityRepository(db)
    city = city_repo.get_by_id(city_id)

    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    obs = (
        db.query(Observation)
        .filter(Observation.city_id == city_id)
        .order_by(Observation.observed_at.desc())
        .first()
    )

    if not obs:
        raise HTTPException(
            status_code=404,
            detail="No observations found for this city",
        )

    pollutants = {
        value.pollutant: PollutantValueOut(
            value=float(value.value),
            unit=value.unit,
        )
        for value in obs.values
    }
    aqi_service = AqiService(EpaUsAqiCalculator())

    return LatestObservationOut(
        city=city,
        source=obs.source,
        observed_at=_ensure_timezone(obs.observed_at),
        collected_at=_ensure_timezone(obs.collected_at),
        pollutants=pollutants,
        aqi=aqi_service.assess_observation(obs),
    )

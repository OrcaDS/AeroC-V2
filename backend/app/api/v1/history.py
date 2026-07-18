from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_db
from app.domain.constants import SUPPORTED_POLLUTANTS
from app.models.observation import Observation
from app.repositories.city_repository import CityRepository
from app.schemas.observation import (
    CityHistoryOut,
    HistoryObservationOut,
    PollutantValueOut,
)

router = APIRouter(prefix="/cities", tags=["history"])


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


@router.get("/{city_id}/history", response_model=CityHistoryOut)
def get_city_history(
    city_id: int,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    pollutant: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    city_repo = CityRepository(db)
    city = city_repo.get_by_id(city_id)

    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    if pollutant and pollutant not in SUPPORTED_POLLUTANTS:
        raise HTTPException(status_code=400, detail="Unsupported pollutant")

    query = (
        db.query(Observation)
        .options(selectinload(Observation.values))
        .filter(Observation.city_id == city_id)
    )

    if from_ is not None:
        query = query.filter(Observation.observed_at >= from_)

    if to is not None:
        query = query.filter(Observation.observed_at <= to)

    observations = query.order_by(Observation.observed_at.asc()).all()

    return CityHistoryOut(
        city=city,
        observations=[
            HistoryObservationOut(
                observed_at=_ensure_timezone(observation.observed_at),
                source=observation.source,
                pollutants={
                    value.pollutant: PollutantValueOut(
                        value=float(value.value),
                        unit=value.unit,
                    )
                    for value in observation.values
                    if pollutant is None or value.pollutant == pollutant
                },
            )
            for observation in observations
            if pollutant is None
            or any(value.pollutant == pollutant for value in observation.values)
        ],
    )

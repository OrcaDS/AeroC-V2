from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.repositories.city_repository import CityRepository
from app.repositories.observation_repository import ObservationRepository
from app.schemas.trend import CityTrendAssessmentOut
from app.services.trend_calculators import TrendDirectionPolicy, WindowTrendCalculator
from app.services.trend_service import TrendService

router = APIRouter(prefix="/cities", tags=["trends"])


@router.get("/{city_id}/trends", response_model=CityTrendAssessmentOut)
def get_city_trends(
    city_id: int,
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    service = TrendService(
        city_repository=CityRepository(db),
        observation_repository=ObservationRepository(db),
        calculator=WindowTrendCalculator(TrendDirectionPolicy()),
    )
    assessment = service.assess_city_trends(city_id=city_id, days=days)

    if assessment is None:
        raise HTTPException(status_code=404, detail="City not found")

    return assessment

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.repositories.city_repository import CityRepository
from app.repositories.observation_repository import ObservationRepository
from app.schemas.dashboard import DashboardOut
from app.services.aqi_calculators import EpaUsAqiCalculator
from app.services.aqi_service import AqiService
from app.services.dashboard_service import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    city_repository = CityRepository(db)
    observation_repository = ObservationRepository(db)
    aqi_service = AqiService(EpaUsAqiCalculator())
    service = DashboardService(
        city_repository,
        observation_repository,
        aqi_service,
    )
    return service.build_dashboard()

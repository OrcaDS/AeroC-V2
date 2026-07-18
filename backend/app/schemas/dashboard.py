from datetime import datetime

from pydantic import BaseModel

from app.schemas.aqi import AqiAssessmentOut
from app.schemas.city import CityOut
from app.schemas.observation import PollutantValueOut


class DashboardAverageOut(BaseModel):
    value: float | None
    unit: str | None


class DashboardSummaryOut(BaseModel):
    cities_monitored: int
    cities_with_current_data: int
    last_observed_at: datetime | None
    average_pm2_5: DashboardAverageOut
    average_pm10: DashboardAverageOut


class DashboardLeaderOut(BaseModel):
    city_id: int
    city_name: str
    value: float
    unit: str
    observed_at: datetime


class DashboardAqiLeaderOut(BaseModel):
    city_id: int
    city_name: str
    observed_at: datetime
    aqi: AqiAssessmentOut


class DashboardLeadersOut(BaseModel):
    highest_pm2_5: DashboardLeaderOut | None
    highest_pm10: DashboardLeaderOut | None
    highest_ozone: DashboardLeaderOut | None
    highest_aqi: DashboardAqiLeaderOut | None


class DashboardCityLatestOut(BaseModel):
    observed_at: datetime
    source: str
    pollutants: dict[str, PollutantValueOut]
    aqi: AqiAssessmentOut | None


class DashboardCityOut(BaseModel):
    city: CityOut
    latest: DashboardCityLatestOut | None


class DashboardOut(BaseModel):
    generated_at: datetime
    summary: DashboardSummaryOut
    leaders: DashboardLeadersOut
    cities: list[DashboardCityOut]

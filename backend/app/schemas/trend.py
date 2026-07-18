from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.city import CityOut


class TrendWindowOut(BaseModel):
    current_start: datetime
    current_end: datetime
    baseline_start: datetime
    baseline_end: datetime


class TrendValueOut(BaseModel):
    value: float
    unit: str


class PollutantTrendOut(BaseModel):
    pollutant: str
    status: str
    current_average: TrendValueOut | None
    baseline_average: TrendValueOut | None
    absolute_change: TrendValueOut | None
    percent_change: float | None
    direction: str | None
    current_observation_count: int
    baseline_observation_count: int

    model_config = ConfigDict(from_attributes=True)


class CityTrendAssessmentOut(BaseModel):
    city: CityOut
    window: TrendWindowOut
    trends: dict[str, PollutantTrendOut]

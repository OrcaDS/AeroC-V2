from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.schemas.aqi import AqiAssessmentOut
from app.schemas.city import CityOut


class PollutantValueOut(BaseModel):
    value: float | None
    unit: str


class ObservationValueOut(BaseModel):
    pollutant: str
    value: float
    unit: str

    model_config = ConfigDict(from_attributes=True)

class ObservationOut(BaseModel):
    id: int
    city_id: int
    source: str
    observed_at: datetime
    values: list[ObservationValueOut]

    model_config = ConfigDict(from_attributes=True)


class LatestObservationOut(BaseModel):
    city: CityOut
    source: str
    observed_at: datetime
    collected_at: datetime
    pollutants: dict[str, PollutantValueOut]
    aqi: AqiAssessmentOut | None


class HistoryObservationOut(BaseModel):
    observed_at: datetime
    source: str
    pollutants: dict[str, PollutantValueOut]


class CityHistoryOut(BaseModel):
    city: CityOut
    observations: list[HistoryObservationOut]

from pydantic import BaseModel, ConfigDict


class CityOut(BaseModel):
    id: int
    code: str
    timezone: str
    name: str
    country: str
    latitude: float
    longitude: float
    active: bool

    model_config = ConfigDict(from_attributes=True)

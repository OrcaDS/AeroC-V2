from pydantic import BaseModel, ConfigDict


class AqiCategoryOut(BaseModel):
    code: str
    label: str
    color: str

    model_config = ConfigDict(from_attributes=True)


class AqiSubIndexOut(BaseModel):
    pollutant: str
    value: int
    category: AqiCategoryOut

    model_config = ConfigDict(from_attributes=True)


class AqiAssessmentOut(BaseModel):
    standard: str
    estimated: bool
    limitations: list[str]
    value: int | None
    category: AqiCategoryOut | None
    primary_pollutant: str | None
    computed_pollutants: list[str]
    sub_indices: dict[str, AqiSubIndexOut]

    model_config = ConfigDict(from_attributes=True)

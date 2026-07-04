"""
Canonical domain enumerations used throughout AeroC.

External providers may use different names for pollutants,
units, or data sources. Collectors are responsible for
translating provider-specific values into these canonical enums.
"""

from enum import StrEnum


class PollutantCode(StrEnum):
    PM25 = "PM25"
    PM10 = "PM10"
    O3 = "O3"
    NO2 = "NO2"
    SO2 = "SO2"
    CO = "CO"


class MeasurementUnit(StrEnum):
    UG_M3 = "µg/m³"
    PPB = "ppb"
    PPM = "ppm"


class DataProvider(StrEnum):
    OPEN_METEO = "Open-Meteo"
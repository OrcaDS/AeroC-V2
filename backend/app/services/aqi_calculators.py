"""
AQI calculators.

The v1 calculator follows the U.S. EPA AQI breakpoint formula and category
scheme. It currently computes AQI only from PM2.5 and PM10 because those are
the pollutants whose persisted units already align with the EPA breakpoint
table used here (micrograms per cubic meter). Gaseous pollutants collected from
Open-Meteo are intentionally excluded until AeroC has the unit conversions and
averaging semantics needed for a defensible implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import trunc

from app.domain.aqi import AqiAssessment, AqiCategory, AqiSubIndex
from app.dto import PollutantReading

EPA_US_STANDARD = "epa_us"
EPA_PM_ONLY_POLLUTANTS = ("pm2_5", "pm10")
ESTIMATED_AQI_LIMITATIONS = (
    "Derived from available PM2.5 and PM10 model observations.",
    "Not an official EPA AQI.",
    "Does not apply EPA-required 24-hour or NowCast averaging.",
    "Does not include gaseous pollutant sub-indices.",
)


@dataclass(slots=True, frozen=True)
class _Breakpoint:
    concentration_low: float
    concentration_high: float
    index_low: int
    index_high: int


EPA_CATEGORIES = (
    AqiCategory(code="good", label="Good", color="#00E400"),
    AqiCategory(code="moderate", label="Moderate", color="#FFFF00"),
    AqiCategory(
        code="unhealthy_for_sensitive_groups",
        label="Unhealthy for Sensitive Groups",
        color="#FF7E00",
    ),
    AqiCategory(code="unhealthy", label="Unhealthy", color="#FF0000"),
    AqiCategory(code="very_unhealthy", label="Very Unhealthy", color="#8F3F97"),
    AqiCategory(code="hazardous", label="Hazardous", color="#7E0023"),
)

PM25_BREAKPOINTS = (
    _Breakpoint(0.0, 9.0, 0, 50),
    _Breakpoint(9.1, 35.4, 51, 100),
    _Breakpoint(35.5, 55.4, 101, 150),
    _Breakpoint(55.5, 125.4, 151, 200),
    _Breakpoint(125.5, 225.4, 201, 300),
    _Breakpoint(225.5, 325.4, 301, 500),
)

PM10_BREAKPOINTS = (
    _Breakpoint(0, 54, 0, 50),
    _Breakpoint(55, 154, 51, 100),
    _Breakpoint(155, 254, 101, 150),
    _Breakpoint(255, 354, 151, 200),
    _Breakpoint(355, 424, 201, 300),
    _Breakpoint(425, 604, 301, 500),
)


class EpaUsAqiCalculator:
    """
    Calculate an EPA-style AQI assessment from AeroC pollutant readings.

    References:
    - AirNow AQI basics
    - EPA/AirNow Technical Assistance Document for the Reporting of Daily Air
      Quality – the Air Quality Index (May 2026)
    """

    def calculate(
        self,
        pollutant_readings: dict[str, PollutantReading],
    ) -> AqiAssessment:
        sub_indices: dict[str, AqiSubIndex] = {}

        pm25_reading = pollutant_readings.get("pm2_5")
        if pm25_reading is not None:
            sub_index = self._build_sub_index(
                pollutant="pm2_5",
                reading=pm25_reading,
                expected_unit="ug/m3",
                breakpoints=PM25_BREAKPOINTS,
                truncate_decimals=1,
            )
            if sub_index is not None:
                sub_indices["pm2_5"] = sub_index

        pm10_reading = pollutant_readings.get("pm10")
        if pm10_reading is not None:
            sub_index = self._build_sub_index(
                pollutant="pm10",
                reading=pm10_reading,
                expected_unit="ug/m3",
                breakpoints=PM10_BREAKPOINTS,
                truncate_decimals=0,
            )
            if sub_index is not None:
                sub_indices["pm10"] = sub_index

        if not sub_indices:
            return AqiAssessment(
                standard=EPA_US_STANDARD,
                estimated=True,
                limitations=ESTIMATED_AQI_LIMITATIONS,
                value=None,
                category=None,
                primary_pollutant=None,
                computed_pollutants=(),
                sub_indices={},
            )

        primary = max(sub_indices.values(), key=lambda sub_index: sub_index.value)
        return AqiAssessment(
            standard=EPA_US_STANDARD,
            estimated=True,
            limitations=ESTIMATED_AQI_LIMITATIONS,
            value=primary.value,
            category=primary.category,
            primary_pollutant=primary.pollutant,
            computed_pollutants=tuple(sub_indices.keys()),
            sub_indices=sub_indices,
        )

    def _build_sub_index(
        self,
        pollutant: str,
        reading: PollutantReading,
        expected_unit: str,
        breakpoints: tuple[_Breakpoint, ...],
        truncate_decimals: int,
    ) -> AqiSubIndex | None:
        if reading.value is None or self._normalize_unit(reading.unit) != expected_unit:
            return None

        truncated_value = self._truncate(reading.value, truncate_decimals)
        breakpoint = self._find_breakpoint(truncated_value, breakpoints)

        if breakpoint is None:
            return None

        index_value = round(
            (
                (breakpoint.index_high - breakpoint.index_low)
                / (breakpoint.concentration_high - breakpoint.concentration_low)
            )
            * (truncated_value - breakpoint.concentration_low)
            + breakpoint.index_low
        )

        category = self._category_for_index(index_value)
        return AqiSubIndex(
            pollutant=pollutant,
            value=index_value,
            category=category,
        )

    @staticmethod
    def _truncate(value: float, decimals: int) -> float:
        factor = 10**decimals
        return trunc(value * factor) / factor

    @staticmethod
    def _normalize_unit(unit: str) -> str:
        """Accept provider and legacy Unicode spellings of micrograms per m³.

        Open-Meteo returns ``μg/m³`` while early AeroC tests and persisted
        records may use ``ug/m3``. AQI calculation is unit-sensitive, but these
        spellings represent the same concentration unit.
        """
        return (
            unit.strip()
            .lower()
            .replace("μ", "u")
            .replace("µ", "u")
            .replace("³", "3")
            .replace(" ", "")
        )

    @staticmethod
    def _find_breakpoint(
        value: float,
        breakpoints: tuple[_Breakpoint, ...],
    ) -> _Breakpoint | None:
        for breakpoint in breakpoints:
            if breakpoint.concentration_low <= value <= breakpoint.concentration_high:
                return breakpoint
        return None

    @staticmethod
    def _category_for_index(index_value: int) -> AqiCategory:
        if index_value <= 50:
            return EPA_CATEGORIES[0]
        if index_value <= 100:
            return EPA_CATEGORIES[1]
        if index_value <= 150:
            return EPA_CATEGORIES[2]
        if index_value <= 200:
            return EPA_CATEGORIES[3]
        if index_value <= 300:
            return EPA_CATEGORIES[4]
        return EPA_CATEGORIES[5]

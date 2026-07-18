"""
AQI service orchestration.

This service keeps endpoint code free of AQI calculation details and provides a
stable application boundary for AQI-related domain capabilities.
"""

from app.domain.aqi import AqiAssessment
from app.dto import PollutantReading
from app.services.aqi_calculators import EpaUsAqiCalculator


class AqiService:
    def __init__(self, calculator: EpaUsAqiCalculator) -> None:
        self.calculator = calculator

    def assess_observation(self, observation) -> AqiAssessment:
        pollutant_readings = {
            value.pollutant: PollutantReading(
                value=float(value.value) if value.value is not None else None,
                unit=value.unit,
            )
            for value in observation.values
        }
        return self.calculator.calculate(pollutant_readings)

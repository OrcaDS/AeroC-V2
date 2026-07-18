"""
Trend calculators and policies.

v1 trend analysis compares pollutant averages between two adjacent windows of
equal duration. The calculator computes the underlying numbers; direction is a
separate policy decision so the sensitivity threshold can evolve without
changing the mathematical definitions.
"""

from dataclasses import dataclass
from statistics import mean

from app.domain.trend import PollutantTrend, TrendValue


@dataclass(slots=True, frozen=True)
class TrendDirectionPolicy:
    flat_threshold_percent: float = 5.0

    def classify(self, percent_change: float | None) -> str | None:
        if percent_change is None:
            return None
        if abs(percent_change) < self.flat_threshold_percent:
            return "flat"
        if percent_change > 0:
            return "up"
        return "down"


@dataclass(slots=True, frozen=True)
class TrendSufficiencyPolicy:
    minimum_observations_per_window: int = 2

    def has_enough_data(
        self,
        current_count: int,
        baseline_count: int,
        unit: str | None,
    ) -> bool:
        return (
            unit is not None
            and current_count >= self.minimum_observations_per_window
            and baseline_count >= self.minimum_observations_per_window
        )


class WindowTrendCalculator:
    def __init__(
        self,
        direction_policy: TrendDirectionPolicy,
        sufficiency_policy: TrendSufficiencyPolicy | None = None,
    ) -> None:
        self.direction_policy = direction_policy
        self.sufficiency_policy = sufficiency_policy or TrendSufficiencyPolicy()

    def calculate(
        self,
        pollutant: str,
        unit: str | None,
        current_values: list[float],
        baseline_values: list[float],
    ) -> PollutantTrend:
        if not self.sufficiency_policy.has_enough_data(
            current_count=len(current_values),
            baseline_count=len(baseline_values),
            unit=unit,
        ):
            return PollutantTrend(
                pollutant=pollutant,
                status="insufficient_data",
                current_average=None,
                baseline_average=None,
                absolute_change=None,
                percent_change=None,
                direction=None,
                current_observation_count=len(current_values),
                baseline_observation_count=len(baseline_values),
            )

        current_average = round(mean(current_values), 2)
        baseline_average = round(mean(baseline_values), 2)
        absolute_change = round(current_average - baseline_average, 2)
        percent_change = None

        if baseline_average != 0:
            percent_change = round(((current_average - baseline_average) / baseline_average) * 100, 2)

        return PollutantTrend(
            pollutant=pollutant,
            status="ok",
            current_average=TrendValue(value=current_average, unit=unit),
            baseline_average=TrendValue(value=baseline_average, unit=unit),
            absolute_change=TrendValue(value=absolute_change, unit=unit),
            percent_change=percent_change,
            direction=self.direction_policy.classify(percent_change),
            current_observation_count=len(current_values),
            baseline_observation_count=len(baseline_values),
        )

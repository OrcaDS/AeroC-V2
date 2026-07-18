from datetime import UTC, datetime, timedelta

from app.domain.constants import SUPPORTED_POLLUTANTS
from app.domain.trend import CityTrendAssessment, TrendWindow
from app.repositories.city_repository import CityRepository
from app.repositories.observation_repository import ObservationRepository
from app.services.trend_calculators import WindowTrendCalculator


class TrendService:
    def __init__(
        self,
        city_repository: CityRepository,
        observation_repository: ObservationRepository,
        calculator: WindowTrendCalculator,
    ) -> None:
        self.city_repository = city_repository
        self.observation_repository = observation_repository
        self.calculator = calculator

    def assess_city_trends(self, city_id: int, days: int) -> CityTrendAssessment | None:
        city = self.city_repository.get_by_id(city_id)
        if city is None:
            return None

        latest_observation = self.observation_repository.get_latest_for_city(city_id)
        anchor = self._ensure_timezone(
            latest_observation.observed_at if latest_observation is not None else datetime.now(UTC)
        )

        current_end = anchor
        current_start = current_end - timedelta(days=days)
        baseline_end = current_start
        baseline_start = baseline_end - timedelta(days=days)

        observations = self.observation_repository.get_for_city_between(
            city_id=city_id,
            start=baseline_start,
            end=current_end,
        )

        current_buckets: dict[str, list[float]] = {pollutant: [] for pollutant in SUPPORTED_POLLUTANTS}
        baseline_buckets: dict[str, list[float]] = {pollutant: [] for pollutant in SUPPORTED_POLLUTANTS}
        units: dict[str, str | None] = {pollutant: None for pollutant in SUPPORTED_POLLUTANTS}

        for observation in observations:
            observed_at = self._ensure_timezone(observation.observed_at)
            target = None
            if baseline_start <= observed_at < baseline_end:
                target = baseline_buckets
            elif current_start <= observed_at <= current_end:
                target = current_buckets

            if target is None:
                continue

            for value in observation.values:
                if value.pollutant not in target:
                    continue
                if value.value is None:
                    continue
                target[value.pollutant].append(float(value.value))
                units[value.pollutant] = value.unit

        trends = {
            pollutant: self.calculator.calculate(
                pollutant=pollutant,
                unit=units[pollutant],
                current_values=current_buckets[pollutant],
                baseline_values=baseline_buckets[pollutant],
            )
            for pollutant in SUPPORTED_POLLUTANTS
        }

        return CityTrendAssessment(
            city=city,
            window=TrendWindow(
                current_start=current_start,
                current_end=current_end,
                baseline_start=baseline_start,
                baseline_end=baseline_end,
            ),
            trends=trends,
        )

    @staticmethod
    def _ensure_timezone(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

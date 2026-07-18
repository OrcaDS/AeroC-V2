from datetime import UTC, datetime

from app.services.aqi_service import AqiService
from app.repositories.city_repository import CityRepository
from app.repositories.observation_repository import ObservationRepository
from app.schemas.dashboard import (
    DashboardAqiLeaderOut,
    DashboardAverageOut,
    DashboardCityLatestOut,
    DashboardCityOut,
    DashboardLeaderOut,
    DashboardLeadersOut,
    DashboardOut,
    DashboardSummaryOut,
)
from app.schemas.observation import PollutantValueOut


class DashboardService:
    def __init__(
        self,
        city_repository: CityRepository,
        observation_repository: ObservationRepository,
        aqi_service: AqiService,
    ) -> None:
        self.city_repository = city_repository
        self.observation_repository = observation_repository
        self.aqi_service = aqi_service

    def build_dashboard(self) -> DashboardOut:
        cities = self.city_repository.get_active()
        latest_observations = self.observation_repository.get_latest_for_city_ids(
            [city.id for city in cities]
        )
        latest_by_city_id = {
            observation.city_id: observation for observation in latest_observations
        }

        city_entries = [
            DashboardCityOut(
                city=city,
                latest=self._serialize_latest(latest_by_city_id.get(city.id)),
            )
            for city in cities
        ]

        return DashboardOut(
            generated_at=datetime.now(UTC),
            summary=self._build_summary(latest_observations, len(cities)),
            leaders=self._build_leaders(latest_observations),
            cities=city_entries,
        )

    def _build_summary(
        self,
        observations: list,
        city_count: int,
    ) -> DashboardSummaryOut:
        last_observed_at = None

        if observations:
            last_observed_at = max(
                self._ensure_timezone(observation.observed_at)
                for observation in observations
            )

        return DashboardSummaryOut(
            cities_monitored=city_count,
            cities_with_current_data=len(observations),
            last_observed_at=last_observed_at,
            average_pm2_5=self._build_average(observations, "pm2_5"),
            average_pm10=self._build_average(observations, "pm10"),
        )

    def _build_average(
        self,
        observations: list,
        pollutant: str,
    ) -> DashboardAverageOut:
        readings = []
        unit = None

        for observation in observations:
            for value in observation.values:
                if value.pollutant == pollutant:
                    readings.append(float(value.value))
                    unit = value.unit

        if not readings:
            return DashboardAverageOut(value=None, unit=None)

        average = round(sum(readings) / len(readings), 2)
        return DashboardAverageOut(value=average, unit=unit)

    def _build_leaders(self, observations: list) -> DashboardLeadersOut:
        return DashboardLeadersOut(
            highest_pm2_5=self._build_leader(observations, "pm2_5"),
            highest_pm10=self._build_leader(observations, "pm10"),
            highest_ozone=self._build_leader(observations, "ozone"),
            highest_aqi=self._build_aqi_leader(observations),
        )

    def _build_leader(
        self,
        observations: list,
        pollutant: str,
    ) -> DashboardLeaderOut | None:
        leader = None

        for observation in observations:
            for value in observation.values:
                if value.pollutant != pollutant:
                    continue

                numeric_value = float(value.value)
                if leader is None or numeric_value > leader["value"]:
                    leader = {
                        "city_id": observation.city.id,
                        "city_name": observation.city.name,
                        "value": numeric_value,
                        "unit": value.unit,
                        "observed_at": self._ensure_timezone(observation.observed_at),
                    }

        if leader is None:
            return None

        return DashboardLeaderOut(**leader)

    def _serialize_latest(self, observation) -> DashboardCityLatestOut | None:
        if observation is None:
            return None

        return DashboardCityLatestOut(
            observed_at=self._ensure_timezone(observation.observed_at),
            source=observation.source,
            pollutants={
                value.pollutant: PollutantValueOut(
                    value=float(value.value),
                    unit=value.unit,
                )
                for value in observation.values
            },
            aqi=self.aqi_service.assess_observation(observation),
        )

    def _build_aqi_leader(self, observations: list) -> DashboardAqiLeaderOut | None:
        leader = None

        for observation in observations:
            assessment = self.aqi_service.assess_observation(observation)
            if assessment.value is None:
                continue

            if leader is None or assessment.value > leader["aqi"].value:
                leader = {
                    "city_id": observation.city.id,
                    "city_name": observation.city.name,
                    "observed_at": self._ensure_timezone(observation.observed_at),
                    "aqi": assessment,
                }

        if leader is None:
            return None

        return DashboardAqiLeaderOut(**leader)

    @staticmethod
    def _ensure_timezone(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

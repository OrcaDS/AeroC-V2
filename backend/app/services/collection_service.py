"""
Coordinates a complete observation collection workflow.

The CollectionService orchestrates collectors, repositories, and
domain models. It contains business logic but no HTTP or SQL.
"""

import logging

from app.ingestion.collectors.open_meteo import OpenMeteoCollector
from app.models.observation import Observation
from app.models.observation_value import ObservationValue
from app.repositories.observation_repository import ObservationRepository

logger = logging.getLogger(__name__)


class CollectionService:
    """Coordinates observation collection for monitored cities."""

    def __init__(
        self,
        observation_repository: ObservationRepository,
        collector: OpenMeteoCollector,
        run_id: str | None = None,
    ) -> None:

        self.observation_repository = observation_repository
        self.collector = collector
        self.run_id = run_id

    def collect_city(self, city) -> bool:
        """
        Collect and persist observations for a single city.
        """

        logger.info(
            "event=city_collection_started run_id=%s city_id=%s city_name=%s provider=%s",
            self.run_id,
            city.id,
            city.name,
            self.collector.__class__.__name__,
            extra={
                "event": "city_collection_started",
                "run_id": self.run_id,
                "city_id": city.id,
                "city_name": city.name,
                "provider": self.collector.__class__.__name__,
            },
        )

        # 1. Fetch from external API
        result = self.collector.fetch(
            latitude=city.latitude,
            longitude=city.longitude,
        )

        # 2. Create Observation ORM object
        observation = Observation(
            city_id=city.id,
            source=result.source,
            observed_at=result.observed_at,
        )

        # 3. Attach pollutant values
        for pollutant, reading in result.values.items():
            observation.values.append(
                ObservationValue(
                    pollutant=pollutant,
                    value=reading.value,
                    unit=reading.unit,
                )
            )

        # 4. Persist only the first AeroC snapshot for this provider-valid hour.
        created = self.observation_repository.create_if_absent(observation)

        logger.info(
            "event=city_persistence_%s run_id=%s city_id=%s city_name=%s observed_at=%s pollutant_count=%s",
            "created" if created else "duplicate_skipped",
            self.run_id,
            city.id,
            city.name,
            result.observed_at.isoformat(),
            len(result.values),
            extra={
                "event": "city_persistence_created" if created else "city_persistence_duplicate_skipped",
                "run_id": self.run_id,
                "city_id": city.id,
                "city_name": city.name,
                "observed_at": result.observed_at.isoformat(),
                "pollutant_count": len(result.values),
            },
        )
        return created

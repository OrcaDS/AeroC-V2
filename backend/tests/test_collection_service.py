from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from app.dto import CollectedObservation, PollutantReading
from app.services.collection_service import CollectionService


@pytest.mark.parametrize("created", [True, False])
def test_collect_city_persists_provider_result_and_returns_outcome(
    seeded_city,
    created,
):
    collector = Mock()
    collector.fetch.return_value = CollectedObservation(
        source="open-meteo",
        observed_at=datetime(2026, 7, 19, 12, tzinfo=UTC),
        values={
            "pm2_5": PollutantReading(value=18.5, unit="ug/m3"),
            "pm10": PollutantReading(value=27.0, unit="ug/m3"),
        },
    )
    observation_repository = Mock()
    observation_repository.create_if_absent.return_value = created
    service = CollectionService(
        observation_repository=observation_repository,
        collector=collector,
        run_id="test-run",
    )

    assert service.collect_city(seeded_city) is created

    collector.fetch.assert_called_once_with(
        latitude=seeded_city.latitude,
        longitude=seeded_city.longitude,
    )
    observation = observation_repository.create_if_absent.call_args.args[0]
    assert observation.city_id == seeded_city.id
    assert observation.source == "open-meteo"
    assert observation.observed_at == datetime(2026, 7, 19, 12, tzinfo=UTC)
    assert [(value.pollutant, value.value, value.unit) for value in observation.values] == [
        ("pm2_5", 18.5, "ug/m3"),
        ("pm10", 27.0, "ug/m3"),
    ]

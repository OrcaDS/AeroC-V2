"""
Simple integration test for the Open-Meteo collector.

This script verifies that the collector can successfully retrieve
and normalize air quality data from Open-Meteo.
"""

from pprint import pprint

from app.ingestion.collectors.open_meteo import OpenMeteoCollector


def main() -> None:
    collector = OpenMeteoCollector()

    result = collector.fetch(
        latitude=14.5995,
        longitude=120.9842,
    )

    pprint(result)


if __name__ == "__main__":
    main()
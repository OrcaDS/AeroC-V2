"""
Bootstrap the AeroC monitoring network.

This script inserts the official monitoring cities into the database.
It is safe to run multiple times.

"""

import app.models
from app.database.session import SessionLocal
from app.models.city import City
from app.repositories.city_repository import CityRepository
from scripts.seed_data.cities import CITIES


def main() -> None:
    session = SessionLocal()
    repository = CityRepository(session)

    inserted = 0
    skipped = 0

    try:
        for city_data in CITIES:

            existing = repository.get_by_code(city_data["code"])

            if existing:
                skipped += 1
                continue

            city = City(**city_data)

            repository.add(city)
            inserted += 1

        session.commit()

        print(f"Inserted: {inserted}")
        print(f"Skipped : {skipped}")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()
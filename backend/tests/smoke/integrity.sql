\set ON_ERROR_STOP on

SELECT current_setting('server_version') AS postgres_version;
SELECT version_num AS alembic_revision FROM alembic_version;

DO $$
BEGIN
    IF (SELECT count(*) FROM cities) <> 8 THEN
        RAISE EXCEPTION 'Expected 8 seeded cities';
    END IF;

    IF EXISTS (
        SELECT code FROM cities GROUP BY code HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate city codes found';
    END IF;

    IF EXISTS (
        SELECT city_id, observed_at, source
        FROM observations
        GROUP BY city_id, observed_at, source
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate observation keys found';
    END IF;

    IF EXISTS (
        SELECT observation_id, pollutant
        FROM observation_values
        GROUP BY observation_id, pollutant
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate observation pollutant rows found';
    END IF;

    IF EXISTS (
        SELECT o.id
        FROM observations o
        LEFT JOIN observation_values ov ON ov.observation_id = o.id
        GROUP BY o.id
        HAVING count(ov.id) <> 6
    ) THEN
        RAISE EXCEPTION 'Incomplete observation aggregate found';
    END IF;

    IF EXISTS (
        SELECT ov.id
        FROM observation_values ov
        LEFT JOIN observations o ON o.id = ov.observation_id
        WHERE o.id IS NULL
    ) THEN
        RAISE EXCEPTION 'Orphaned observation values found';
    END IF;

    IF EXISTS (
        SELECT id
        FROM observation_values
        WHERE value < 0 OR value IS NULL OR unit IS NULL OR btrim(unit) = ''
    ) THEN
        RAISE EXCEPTION 'Invalid pollutant value found';
    END IF;

    IF (SELECT count(*) FROM observations) <> 16 THEN
        RAISE EXCEPTION 'Expected 16 final observations';
    END IF;

    IF (SELECT count(*) FROM observation_values) <> 96 THEN
        RAISE EXCEPTION 'Expected 96 final pollutant rows';
    END IF;
END
$$;

SELECT
    count(*) AS city_count,
    count(*) FILTER (WHERE active) AS active_city_count
FROM cities;

SELECT
    count(*) AS observation_count,
    min(observed_at) AS earliest_observation,
    max(observed_at) AS latest_observation
FROM observations;

SELECT
    count(*) AS pollutant_value_count,
    count(DISTINCT pollutant) AS pollutant_types
FROM observation_values;

SELECT
    c.code,
    count(o.id) AS observations,
    max(o.observed_at) AS latest_observed_at
FROM cities c
LEFT JOIN observations o ON o.city_id = c.id
GROUP BY c.id, c.code
ORDER BY c.code;

\set ON_ERROR_STOP on

DO $$
BEGIN
    IF (SELECT count(*) FROM observations) <> 15 THEN
        RAISE EXCEPTION 'Expected 15 observations after partial collection';
    END IF;

    IF (SELECT count(*) FROM observation_values) <> 90 THEN
        RAISE EXCEPTION 'Expected 90 pollutant rows after partial collection';
    END IF;

    IF (
        SELECT count(*)
        FROM (
            SELECT c.code, count(o.id) AS observation_count
            FROM cities c
            LEFT JOIN observations o ON o.city_id = c.id
            GROUP BY c.id, c.code
            HAVING count(o.id) = 2
        ) successful_cities
    ) <> 7 THEN
        RAISE EXCEPTION 'Expected seven cities with two observations';
    END IF;

    IF (
        SELECT count(o.id)
        FROM cities c
        LEFT JOIN observations o ON o.city_id = c.id
        WHERE c.code = 'ID-BDG'
        GROUP BY c.id
    ) <> 1 THEN
        RAISE EXCEPTION 'Expected failed Bandung collection to preserve one observation';
    END IF;
END
$$;

SELECT c.code, count(o.id) AS observation_count
FROM cities c
LEFT JOIN observations o ON o.city_id = c.id
GROUP BY c.id, c.code
ORDER BY c.code;

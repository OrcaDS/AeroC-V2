from app.dto import PollutantReading
from app.services.aqi_calculators import EpaUsAqiCalculator


def test_epa_us_aqi_calculates_pm25_sub_index():
    calculator = EpaUsAqiCalculator()

    assessment = calculator.calculate(
        {"pm2_5": PollutantReading(value=35.9, unit="ug/m3")}
    )

    assert assessment.standard == "epa_us"
    assert assessment.estimated is True
    assert "Not an official EPA AQI." in assessment.limitations
    assert assessment.value == 102
    assert assessment.primary_pollutant == "pm2_5"
    assert assessment.category is not None
    assert assessment.category.code == "unhealthy_for_sensitive_groups"
    assert assessment.computed_pollutants == ("pm2_5",)


def test_epa_us_aqi_chooses_highest_pm_sub_index():
    calculator = EpaUsAqiCalculator()

    assessment = calculator.calculate(
        {
            "pm2_5": PollutantReading(value=35.9, unit="ug/m3"),
            "pm10": PollutantReading(value=200.0, unit="ug/m3"),
        }
    )

    assert assessment.value == 123
    assert assessment.primary_pollutant == "pm10"
    assert assessment.sub_indices["pm2_5"].value == 102
    assert assessment.sub_indices["pm10"].value == 123


def test_epa_us_aqi_truncates_before_calculating():
    calculator = EpaUsAqiCalculator()

    assessment = calculator.calculate(
        {"pm2_5": PollutantReading(value=35.49, unit="ug/m3")}
    )

    assert assessment.value == 100
    assert assessment.category is not None
    assert assessment.category.code == "moderate"


def test_epa_us_aqi_skips_unsupported_units_and_pollutants():
    calculator = EpaUsAqiCalculator()

    assessment = calculator.calculate(
        {
            "ozone": PollutantReading(value=164.0, unit="ug/m3"),
            "pm2_5": PollutantReading(value=24.5, unit="ug/m3"),
        }
    )

    assert assessment.value == 80
    assert assessment.primary_pollutant == "pm2_5"
    assert assessment.computed_pollutants == ("pm2_5",)
    assert "ozone" not in assessment.sub_indices


def test_epa_us_aqi_returns_empty_assessment_without_compatible_pollutants():
    calculator = EpaUsAqiCalculator()

    assessment = calculator.calculate(
        {"ozone": PollutantReading(value=164.0, unit="ug/m3")}
    )

    assert assessment.value is None
    assert assessment.category is None
    assert assessment.primary_pollutant is None
    assert assessment.computed_pollutants == ()
    assert assessment.sub_indices == {}

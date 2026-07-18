from app.services.trend_calculators import (
    TrendDirectionPolicy,
    TrendSufficiencyPolicy,
    WindowTrendCalculator,
)


def test_window_trend_calculator_computes_change_and_direction():
    calculator = WindowTrendCalculator(TrendDirectionPolicy(flat_threshold_percent=5.0))

    trend = calculator.calculate(
        pollutant="pm2_5",
        unit="ug/m3",
        current_values=[30.0, 36.0],
        baseline_values=[20.0, 24.0],
    )

    assert trend.status == "ok"
    assert trend.current_average is not None
    assert trend.current_average.value == 33.0
    assert trend.baseline_average is not None
    assert trend.baseline_average.value == 22.0
    assert trend.absolute_change is not None
    assert trend.absolute_change.value == 11.0
    assert trend.percent_change == 50.0
    assert trend.direction == "up"
    assert trend.current_observation_count == 2
    assert trend.baseline_observation_count == 2


def test_window_trend_calculator_uses_policy_for_flat_direction():
    calculator = WindowTrendCalculator(TrendDirectionPolicy(flat_threshold_percent=5.0))

    trend = calculator.calculate(
        pollutant="pm10",
        unit="ug/m3",
        current_values=[20.0, 20.8],
        baseline_values=[20.0, 20.0],
    )

    assert trend.status == "ok"
    assert trend.percent_change == 2.0
    assert trend.direction == "flat"


def test_window_trend_calculator_returns_insufficient_data_status():
    calculator = WindowTrendCalculator(TrendDirectionPolicy())

    trend = calculator.calculate(
        pollutant="ozone",
        unit="ug/m3",
        current_values=[120.0],
        baseline_values=[],
    )

    assert trend.status == "insufficient_data"
    assert trend.current_average is None
    assert trend.baseline_average is None
    assert trend.absolute_change is None
    assert trend.percent_change is None
    assert trend.direction is None
    assert trend.current_observation_count == 1
    assert trend.baseline_observation_count == 0


def test_window_trend_calculator_requires_minimum_observation_count_per_window():
    calculator = WindowTrendCalculator(
        TrendDirectionPolicy(),
        TrendSufficiencyPolicy(minimum_observations_per_window=2),
    )

    trend = calculator.calculate(
        pollutant="pm2_5",
        unit="ug/m3",
        current_values=[40.0],
        baseline_values=[30.0],
    )

    assert trend.status == "insufficient_data"
    assert trend.current_observation_count == 1
    assert trend.baseline_observation_count == 1


def test_direction_policy_can_classify_downward_change():
    policy = TrendDirectionPolicy(flat_threshold_percent=5.0)

    assert policy.classify(-12.5) == "down"

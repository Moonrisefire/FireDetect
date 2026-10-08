import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from catboost import CatBoostClassifier

from app.core.aoi import point_inside_aoi
from app.ml.predictor import FEATURE_NAMES, build_feature_vector
from app.services.ndvi_calculator import empty_ndvi
from app.services.weather_client import aggregate_daily_features


def test_daily_features_match_notebook_window():
    daily = {
        "temperature_2m_max": [1, 2, 3, None, 10, 20, 30],
        "wind_speed_10m_max": [1, 1, 1, 1, 4, 9, 3],
        "precipitation_sum": [0, 5, 0.2, 0.0, 0.5, None, 0.4],
        "shortwave_radiation_sum": [10, 10, 10, 10, 2, 4, 6],
        "vapor_pressure_deficit_max": [1, 1, 1, 1, 0.5, 1.5, 1.0],
        "soil_moisture_0_to_7cm_mean": [0.2, 0.2, 0.2, 0.2, 0.3, 0.1, 0.2],
    }
    features = aggregate_daily_features(daily, 5)
    assert features["avg_temp_5d"] == (3 + 10 + 20 + 30) / 4
    assert features["max_wind_5d"] == 9
    assert features["total_precip_5d"] == 0.2 + 0.0 + 0.5 + 0.4
    assert features["avg_rad_5d"] == (10 + 10 + 2 + 4 + 6) / 5
    assert features["avg_vpd_5d"] == (1 + 1 + 0.5 + 1.5 + 1.0) / 5
    assert features["avg_soil_moisture_5d"] == (0.2 + 0.2 + 0.3 + 0.1 + 0.2) / 5
    assert features["days_without_rain"] == 1
    assert features["month"] == 5


def test_dry_streak_walks_the_full_series():
    daily = {
        "temperature_2m_max": [0, 0, 0, 0, 0],
        "wind_speed_10m_max": [1, 1, 1, 1, 1],
        "precipitation_sum": [2.0, 0.0, 0.2, 0.0, 0.5],
        "shortwave_radiation_sum": [1, 1, 1, 1, 1],
        "vapor_pressure_deficit_max": [1, 1, 1, 1, 1],
        "soil_moisture_0_to_7cm_mean": [1, 1, 1, 1, 1],
    }
    assert aggregate_daily_features(daily, 1)["days_without_rain"] == 4


def test_cached_forecast_stays_inside_its_window():
    center_lat, center_lon, buffer_deg = 51.5335, 45.9341, 0.25
    assert point_inside_aoi(51.6, 46.0, center_lat, center_lon, buffer_deg)
    assert not point_inside_aoi(55.75, 37.62, center_lat, center_lon, buffer_deg)


def test_feature_vector_matches_saved_model():
    model_path = Path(__file__).resolve().parents[1] / "app" / "ml" / "catboost_fire_model.cbm"
    model = CatBoostClassifier()
    model.load_model(str(model_path))
    assert list(model.feature_names_) == FEATURE_NAMES

    weather = {name: index for index, name in enumerate(FEATURE_NAMES[:7])}
    ndvi = {"mean_ndvi": 0.2, "dry_area_fraction": 0.01}
    vector = build_feature_vector(weather, ndvi, 8)
    assert vector == [0, 1, 2, 3, 4, 5, 6, 8, 0.2, 0.01]


def test_missing_weather_does_not_invent_a_score():
    import main

    with patch.object(main, "WeatherClient") as weather_cls:
        weather_cls.return_value.get_weather = AsyncMock(return_value=None)
        result = asyncio.run(main._run_pipeline(51.5, 46.0))
    assert result is None


def test_missing_scene_feeds_zero_ndvi_into_the_model():
    import main

    weather = {
        "avg_temp_5d": 25,
        "max_wind_5d": 10,
        "total_precip_5d": 0,
        "avg_rad_5d": 15,
        "avg_vpd_5d": 1.2,
        "avg_soil_moisture_5d": 0.1,
        "days_without_rain": 6,
        "month": 7,
        "temperature": 28,
        "humidity": 30,
        "precipitation": 0,
    }

    class Recorder:
        def predict_risk(self, weather_data, ndvi_data, current_month):
            self.ndvi = ndvi_data
            self.month = current_month
            return 0.2, "low"

    recorder = Recorder()
    previous = main.predictor
    try:
        with patch.object(main, "WeatherClient") as weather_cls, patch.object(main, "SatelliteClient") as satellite_cls:
            weather_cls.return_value.get_weather = AsyncMock(return_value=weather)
            satellite_cls.return_value.get_latest_image_urls = AsyncMock(return_value=None)
            main.predictor = recorder
            result = asyncio.run(main._run_pipeline(51.5, 46.0))
    finally:
        main.predictor = previous

    assert result["risk_score"] == 0.2
    assert result["risk_score"] not in (0.02, 0.5)
    assert recorder.ndvi["mean_ndvi"] == 0.0
    assert recorder.ndvi["dry_area_fraction"] == 0.0
    assert recorder.month == 7
    assert empty_ndvi()["problem_areas"] == []


def test_finished_jobs_do_not_grow_without_a_limit():
    import main

    main._jobs.clear()
    main._store_job("live", {"status": "running"})
    for index in range(60):
        main._store_job(f"done-{index}", {"status": "done"})
    assert "live" in main._jobs
    assert len(main._jobs) <= 50

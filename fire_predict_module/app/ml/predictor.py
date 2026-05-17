import os
from typing import Tuple
from catboost import CatBoostClassifier

from ..core import config

class FirePredictor:
    def __init__(self, logger, model_path: str = "app/ml/catboost_fire_model.cbm"):
        self.logger = logger
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """
        Инициализирует и загружает веса CatBoost.
        Вызывается один раз при старте приложения.
        """
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Файл весов модели не найден: {self.model_path}")

            self.logger.info(f"Загрузка ML-модели CatBoost из {self.model_path}...")
            self.model = CatBoostClassifier()
            self.model.load_model(self.model_path)
            self.logger.info("ML-модель успешно загружена и готова к инференсу.")
        except Exception as e:
            self.logger.error("Критическая ошибка при загрузке CatBoost модели", exc_info=True)
            raise e

    def predict_risk(self, weather_data: dict, ndvi_data: dict, current_month: int) -> Tuple[float, str]:
        """
        Формирует строгий вектор фичей и возвращает (risk_score, risk_level).
        """
        if self.model is None:
            raise RuntimeError("Попытка предсказания на незагруженной модели.")

        try:
            features = [
                float(weather_data["avg_temp_5d"]),
                float(weather_data["max_wind_5d"]),
                float(weather_data["total_precip_5d"]),
                float(weather_data["avg_rad_5d"]),
                float(weather_data["avg_vpd_5d"]),
                float(weather_data["avg_soil_moisture_5d"]),
                int(weather_data["days_without_rain"]),
                int(current_month),
                float(ndvi_data["mean_ndvi"]),
                float(ndvi_data["dry_area_fraction"])
            ]

            # Получаем вероятность пожара (класс 1)
            probabilities = self.model.predict_proba([features])
            risk_score = round(float(probabilities[0][1]), 3)

            if risk_score >= config.THRESHOLD_HIGH:
                risk_level = "high"
            elif risk_score >= config.THRESHOLD_MEDIUM:
                risk_level = "medium"
            else:
                risk_level = "low"

            return risk_score, risk_level

        except Exception as e:
            self.logger.error("Ошибка во время инференса CatBoost", exc_info=True)
            raise e
import os

# Настройки масштабирования и региона (по умолчанию Саратов)
DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", 51.5335))
DEFAULT_LON = float(os.getenv("DEFAULT_LON", 45.9341))

# Интервалы и таймауты
PIPELINE_INTERVAL = int(os.getenv("PIPELINE_INTERVAL", 21600))  # 6 часов
API_TIMEOUT = int(os.getenv("API_TIMEOUT", 15))

# Внешние API
WEATHER_API_URL = os.getenv("WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast")
STAC_API_URL = os.getenv("STAC_API_URL", "https://earth-search.aws.element84.com/v1/search")
MAX_CLOUD_COVER = int(os.getenv("MAX_CLOUD_COVER", 30))

# Гео-аналитика и NDVI
NDVI_SCALE_FACTOR = int(os.getenv("NDVI_SCALE_FACTOR", 10))

# ML-контур
MODEL_PATH = os.getenv("MODEL_PATH", "app/ml/catboost_fire_model.cbm")
THRESHOLD_MEDIUM = float(os.getenv("SHAP_THRESHOLD_MEDIUM", 0.4992))
THRESHOLD_HIGH = float(os.getenv("SHAP_THRESHOLD_HIGH", 0.75))
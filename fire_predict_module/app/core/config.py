import os

# Настройки масштабирования и региона (по умолчанию Саратов)
DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", 51.5335))
DEFAULT_LON = float(os.getenv("DEFAULT_LON", 45.9341))

# Интервалы и таймауты
PIPELINE_INTERVAL = int(os.getenv("PIPELINE_INTERVAL", 21600))  # 6 часов
API_TIMEOUT = int(os.getenv("API_TIMEOUT", 15))

# Внешние API
WEATHER_API_URL = os.getenv("WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast")
WEATHER_TIMEZONE = os.getenv("WEATHER_TIMEZONE", "Europe/Moscow")
WEATHER_PAST_DAYS = int(os.getenv("WEATHER_PAST_DAYS", 30))
WEATHER_FORECAST_DAYS = int(os.getenv("WEATHER_FORECAST_DAYS", 1))
STAC_API_URL = os.getenv("STAC_API_URL", "https://earth-search.aws.element84.com/v1/search")
MAX_CLOUD_COVER = int(os.getenv("MAX_CLOUD_COVER", 20))

# Гео-аналитика и NDVI
NDVI_SCALE_FACTOR = int(os.getenv("NDVI_SCALE_FACTOR", 10))
AOI_BUFFER_DEG = float(os.getenv("AOI_BUFFER_DEG", 0.25))

# ML-контур. Порог 0.4992 — рабочая точка F1 из Untitled0_(1).ipynb.
# 0.75 делит medium и high на карте, в ноутбуке этого разреза нет.
MODEL_PATH = os.getenv("MODEL_PATH", "app/ml/catboost_fire_model.cbm")
THRESHOLD_MEDIUM = float(os.getenv("THRESHOLD_MEDIUM", "0.4992"))
THRESHOLD_HIGH = float(os.getenv("THRESHOLD_HIGH", "0.75"))
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import aiohttp

from ..core import config

FEATURE_DAYS = 5
DRY_DAY_MM = 1.0


def moscow_now() -> datetime:
    """Календарь как в обучении: Open-Meteo timezone=Europe/Moscow (UTC+3, без перевода часов)."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(config.WEATHER_TIMEZONE))
    except Exception:
        return datetime.now(timezone(timedelta(hours=3)))


def aggregate_daily_features(daily: dict, month: int) -> Optional[dict]:
    """
    Те же формулы, что в Untitled0_(1).ipynb:
    последние 5 суток суточных полей и сухой хвост по всему ряду.
    """
    if not daily or "temperature_2m_max" not in daily:
        return None

    def last_present(key: str, n: int = FEATURE_DAYS) -> list:
        return [value for value in (daily.get(key) or [])[-n:] if value is not None]

    temps = last_present("temperature_2m_max")
    winds = last_present("wind_speed_10m_max")
    precips = last_present("precipitation_sum")
    rads = last_present("shortwave_radiation_sum")
    vpds = last_present("vapor_pressure_deficit_max")
    soils = last_present("soil_moisture_0_to_7cm_mean")

    days_without_rain = 0
    for precip in reversed(daily.get("precipitation_sum") or []):
        if precip is not None and precip < DRY_DAY_MM:
            days_without_rain += 1
        else:
            break

    return {
        "avg_temp_5d": sum(temps) / len(temps) if temps else 0.0,
        "max_wind_5d": max(winds) if winds else 0.0,
        "total_precip_5d": sum(precips) if precips else 0.0,
        "avg_rad_5d": sum(rads) / len(rads) if rads else 0.0,
        "avg_vpd_5d": sum(vpds) / len(vpds) if vpds else 0.0,
        "avg_soil_moisture_5d": sum(soils) / len(soils) if soils else 0.0,
        "days_without_rain": days_without_rain,
        "month": int(month),
    }


class WeatherClient:
    def __init__(self, logger):
        self.logger = logger
        self.base_url = config.WEATHER_API_URL

    async def get_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """Суточные признаки модели и текущие температура/влажность для карточки."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "past_days": config.WEATHER_PAST_DAYS,
            "forecast_days": config.WEATHER_FORECAST_DAYS,
            "daily": (
                "temperature_2m_max,wind_speed_10m_max,precipitation_sum,"
                "shortwave_radiation_sum,vapor_pressure_deficit_max,soil_moisture_0_to_7cm_mean"
            ),
            "current": "temperature_2m,relative_humidity_2m,precipitation",
            "timezone": config.WEATHER_TIMEZONE,
        }
        try:
            timeout = aiohttp.ClientTimeout(total=config.API_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.base_url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()

            features = aggregate_daily_features(data.get("daily") or {}, moscow_now().month)
            if features is None:
                self.logger.warning("Open-Meteo вернул пустой суточный блок.")
                return None

            current = data.get("current") or {}
            features["temperature"] = current.get("temperature_2m")
            features["humidity"] = current.get("relative_humidity_2m")
            features["precipitation"] = current.get("precipitation")

            self.logger.info("Успешно получены суточные погодные признаки")
            return features

        except Exception:
            self.logger.error("Ошибка при запросе погоды из Open-Meteo API", exc_info=True)
            return None

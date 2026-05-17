import aiohttp
from typing import Dict, Optional

from ..core import config


class WeatherClient:
    def __init__(self, logger):
        self.logger = logger
        self.base_url = config.WEATHER_API_URL

    async def get_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Получает текущую погоду для заданных координат.
        Возвращает словарь с данными или None в случае ошибки.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "past_days": 5,
            "forecast_days": 1,
            "current": "temperature_2m,relative_humidity_2m,precipitation",
            "hourly": "temperature_2m,wind_speed_10m,precipitation,shortwave_radiation,vapor_pressure_deficit,soil_moisture_0_to_7cm",
            "timezone": "auto"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=15) as response:
                    response.raise_for_status()
                    data = await response.json()

                    current = data.get("current", {})
                    hourly = data.get("hourly", {})

                    if not hourly or "temperature_2m" not in hourly:
                        self.logger.warning("Open-Meteo вернул пустой блок почасовых данных.")
                        return None

                    history_hours = 5 * 24

                    raw_temps = hourly.get("temperature_2m", [])[:history_hours]
                    raw_winds = hourly.get("wind_speed_10m", [])[:history_hours]
                    raw_precips = hourly.get("precipitation", [])[:history_hours]
                    raw_rads = hourly.get("shortwave_radiation", [])[:history_hours]
                    raw_vpds = hourly.get("vapor_pressure_deficit", [])[:history_hours]
                    raw_soils = hourly.get("soil_moisture_0_to_7cm", [])[:history_hours]

                    # --- Агрегация фичей под датасет модели ---
                    daily_max_temps = []
                    for i in range(0, history_hours, 24):
                        day_slice = raw_temps[i:i + 24]
                        if day_slice:
                            daily_max_temps.append(max(day_slice))
                    avg_temp_5d = sum(daily_max_temps) / len(daily_max_temps) if daily_max_temps else 0.0

                    max_wind_5d = max(raw_winds) if raw_winds else 0.0
                    total_precip_5d = sum(raw_precips) if raw_precips else 0.0
                    avg_rad_5d = sum(raw_rads) / len(raw_rads) if raw_rads else 0.0
                    avg_vpd_5d = sum(raw_vpds) / len(raw_vpds) if raw_vpds else 0.0
                    avg_soil_moisture_5d = sum(raw_soils) / len(raw_soils) if raw_soils else 0.0

                    daily_precips = []
                    for i in range(0, history_hours, 24):
                        day_slice = raw_precips[i:i + 24]
                        if day_slice:
                            daily_precips.append(sum(day_slice))

                    days_without_rain = 0
                    for p in reversed(daily_precips):
                        if p < 1.0:
                            days_without_rain += 1
                        else:
                            break

                    weather_data = {
                        "avg_temp_5d": round(avg_temp_5d, 2),
                        "max_wind_5d": round(max_wind_5d, 2),
                        "total_precip_5d": round(total_precip_5d, 2),
                        "avg_rad_5d": round(avg_rad_5d, 2),
                        "avg_vpd_5d": round(avg_vpd_5d, 3),
                        "avg_soil_moisture_5d": round(avg_soil_moisture_5d, 3),
                        "days_without_rain": days_without_rain,

                        "precipitation": current.get("precipitation", 0.0),  # <-- И СЮДА
                        "temperature": current.get("temperature_2m", 0.0),
                        "humidity": current.get("relative_humidity_2m", 50.0)
                    }

                    self.logger.info("Успешно получены и агрегированы погодные метрики")
                    return weather_data

        except Exception as e:
            self.logger.error("Ошибка при запросе погоды из Open-Meteo API", exc_info=True)
            return None
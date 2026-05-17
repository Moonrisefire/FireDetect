import aiohttp
import asyncio
from typing import Dict, Optional


class WeatherClient:
    def __init__(self, logger):
        self.logger = logger
        self.base_url = "https://api.open-meteo.com/v1/forecast"

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
            "daily": "temperature_2m_max,wind_speed_10m_max,"
                     "precipitation_sum,shortwave_radiation_sum,vapor_pressure_deficit_max,"
                     "soil_moisture_0_to_7cm_mean, relative_humidity_2m",
            "timezone": "auto"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=15) as response:
                    response.raise_for_status()
                    data = await response.json()

                    daily = data.get("daily", {})
                    if not daily or "temperature_2m_max" not in daily:
                        return None

                    temps = [t for t in daily['temperature_2m_max'][-6:-1] if t is not None]
                    winds = [w for w in daily['wind_speed_10m_max'][-6:-1] if w is not None]
                    precips = [p for p in daily['precipitation_sum'][-6:-1] if p is not None]
                    rads = [r for r in daily['shortwave_radiation_sum'][-6:-1] if r is not None]
                    vpds = [v for v in daily['vapor_pressure_deficit_max'][-6:-1] if v is not None]
                    soils = [s for s in daily['soil_moisture_0_to_7cm_mean'][-6:-1] if s is not None]
                    humidity = [h for h in daily['relative_humidity_2m'][-6:-1] if h is not None]

                    days_without_rain = 0
                    for p in reversed(daily['precipitation_sum'][-6:-1]):
                        if p is not None and p < 1.0:
                            days_without_rain += 1
                        else:
                            break

                    weather_data = {
                        "avg_temp_5d": sum(temps) / len(temps) if temps else 0.0,
                        "max_wind_5d": max(winds) if winds else 0.0,
                        "total_precip_5d": sum(precips) if precips else 0.0,
                        "avg_rad_5d": sum(rads) / len(rads) if rads else 0.0,
                        "avg_vpd_5d": sum(vpds) / len(vpds) if vpds else 0.0,
                        "avg_soil_moisture_5d": sum(soils) / len(soils) if soils else 0.0,
                        "days_without_rain": days_without_rain,
                        "temperature": sum(temps)/ len(temps) if temps else 0.0,
                        "humidity": sum(humidity)/ len(humidity) if humidity else 0.0,
                    }

                    self.logger.info("Успешно получены 5-дневные данные",
                                     extra={"extra_data": {"coords": f"{lat},{lon}"}})
                    return weather_data

        except Exception as e:
            self.logger.error("Ошибка при запросе погоды", exc_info=True)
            return None
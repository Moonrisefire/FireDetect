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
            "current": "temperature_2m,relative_humidity_2m,precipitation,"
                       "wind_speed_10m,soil_temperature_0cm,soil_moisture_0_to_7cm,"
                       "vapor_pressure_deficit,shortwave_radiation",
            "timezone": "auto"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=15) as response:
                    response.raise_for_status()
                    data = await response.json()

                    current = data.get("current", {})

                    weather_data = {
                        "temperature": current.get("temperature_2m"),
                        "humidity": current.get("relative_humidity_2m"),
                        "precipitation": current.get("precipitation"),
                        "wind_speed": current.get("wind_speed_10m"),
                        "soil_temperature": current.get("soil_temperature_0cm"),
                        "soil_moisture": current.get("soil_moisture_0_to_7cm"),
                        "vapor_pressure": current.get("vapor_pressure_deficit"),
                        "shortwave_radiation": current.get("shortwave_radiation")
                    }

                    self.logger.info("Успешно получены данные о погоде", extra = {"extra_data" : { "coords": f"{lat},{lon}"}})
                    return weather_data

        except asyncio.TimeoutError:
            self.logger.error("Таймаут при запросе погоды", exc_info=True, extra = {"extra_data" : {"lat": lat, "lon": lon}})
            return None
        except aiohttp.ClientError as e:
            self.logger.error("Сетевая ошибка при запросе погоды", exc_info=True, extra = {"extra_data" : {"error": str(e)}})
            return None
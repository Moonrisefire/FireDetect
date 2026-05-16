import aiohttp
from datetime import datetime, timedelta, timezone

class SatelliteClient:
    def __init__(self, logger):
        self.logger = logger
        self.stac_url = "https://earth-search.aws.element84.com/v1/search"

    async def get_latest_image_urls(self, lat: float, lon: float, max_cloud_cover: int = 15):
        """
        Ищет последний безоблачный снимок за последние 15 дней.
        Возвращает прямые ссылки на Red (B04) и NIR (B08) каналы.
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=15)
        date_range = f"{start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"

        payload = {
            "collections": ["sentinel-2-l2a"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "datetime": date_range,
            "query": {"eo:cloud_cover": {"lt": max_cloud_cover}},
            "limit": 1,
            "sortby": [{"field": "properties.datetime", "direction": "desc"}]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.stac_url, json=payload, timeout=20) as response:
                    response.raise_for_status()
                    data = await response.json()

                    if not data.get("features"):
                        self.logger.warning("Нет подходящих снимков (возможно, всё в облаках)",
                                            extra={"extra_data": {"lat": lat, "lon": lon}})
                        return None

                    best_scene = data["features"][0]
                    assets = best_scene["assets"]

                    urls = {
                        "date": best_scene["properties"]["datetime"],
                        "red_url": assets["red"]["href"],
                        "nir_url": assets["nir"]["href"]
                    }

                    self.logger.info("Найден подходящий снимок", extra={"extra_data": {"date": urls["date"]}})
                    return urls

        except Exception as e:
            self.logger.error("Ошибка при поиске снимка в STAC API", exc_info=True)
            return None
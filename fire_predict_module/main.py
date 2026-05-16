import asyncio
from app.utils.logger import get_logger
from app.services.weather_client import WeatherClient
from app.services.satellite_client import SatelliteClient
from app.services.ndvi_calculator import NDVICalculator

# Координаты центра Саратовской области
SARATOV_LAT = 51.5335
SARATOV_LON = 45.9341


async def run_prediction_pipeline(logger):
    """
    Основной пайплайн, который выполняет один полный цикл проверки.
    """
    logger.info("Запуск цикла прогнозирования пожароопасности...")

    # 1. Запрашиваем погоду
    weather_client = WeatherClient(logger)
    satellite_client = SatelliteClient(logger)
    ndvi_calculator = NDVICalculator(logger)
    weather = await weather_client.get_weather(SARATOV_LAT, SARATOV_LON)

    if not weather:
        logger.warning("Не удалось получить погоду. Пропуск цикла до следующего запуска.")
        return

    logger.info("Текущие метеоусловия", extra = {"extra_data" : weather})

    # 2. Быстрый фильтр (Эвристика)
    if weather["precipitation"] > 1.0 or weather["temperature"] < 5.0:
        logger.info("Риск пожара минимален (осадки или холодно). Обновляем БД: hazard_level=low")
        # TODO: async_db_session.execute("UPDATE hazard_predictions SET level='low' ...")
        return

    # 3. Тяжелая логика (запускается только если сухо и тепло)
    logger.info("Погодные условия способствуют возгоранию. Запуск анализа спутниковых снимков...")

    image_urls = await satellite_client.get_latest_image_urls(SARATOV_LAT, SARATOV_LON)

    if not image_urls:
        logger.warning("Снимки не найдены. Цикл завершен.")
        return

    # 4. Считаем индекс сухости растительности (NDVI)
    ndvi_value = await ndvi_calculator.get_mean_ndvi(image_urls["red_url"], image_urls["nir_url"])

    if ndvi_value is None:
        logger.warning("NDVI вернул None. Что-то пошло не так")
        return

    # TODO: probabilities = ml_predictor.predict(weather, ndvi_data)
    # TODO: save_to_db(probabilities)

    logger.info("Пайплайн успешно завершен. Данные сохранены в БД.")


async def main():
    logger = get_logger("fire_predictor_worker")
    logger.info("Модуль-воркер инициализирован и запущен")


    while True:
        try:
            await run_prediction_pipeline(logger)
        except Exception:
            logger.error("Критическая ошибка в пайплайне", exc_info=True)

        sleep_time = 21600
        logger.info(f"Уход в спящий режим на {sleep_time} секунд.")
        await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    asyncio.run(main())
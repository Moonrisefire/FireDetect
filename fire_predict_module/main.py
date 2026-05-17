import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.utils.logger import get_logger
from app.services.weather_client import WeatherClient
from app.services.satellite_client import SatelliteClient
from app.services.ndvi_calculator import NDVICalculator
from app.ml.predictor import FirePredictor

SARATOV_LAT = 51.5335
SARATOV_LON = 45.9341
PIPELINE_INTERVAL = 21600  # 6 hours

_latest_result: dict | None = None
_pipeline_running: bool = False
_jobs: dict[str, dict] = {}

logger = get_logger("fire_predictor_api")

predictor: FirePredictor | None = None

class AnalyzeRequest(BaseModel):
    lat: float
    lon: float


async def _run_pipeline(lat: float, lon: float) -> dict | None:
    weather_client = WeatherClient(logger)
    satellite_client = SatelliteClient(logger)
    ndvi_calculator = NDVICalculator(logger)

    weather = await weather_client.get_weather(lat, lon)
    if not weather:
        logger.warning("Не удалось получить погоду.")
        return None

    logger.info("Текущие метеоусловия", extra={"extra_data": weather})

    if weather["precipitation"] > 1.0 or weather["temperature"] < 5.0:
        logger.info("Риск пожара минимален (осадки или холодно).")
        return {
            "status": "ok",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "weather": weather,
            "risk_level": "low",
            "risk_score": 0.02,
            "center_lat": lat,
            "center_lon": lon,
            "ndvi": None,
            "problem_areas": [],
        }

    logger.info("Запуск анализа спутниковых снимков...")
    image_urls = await satellite_client.get_latest_image_urls(lat, lon)

    if not image_urls:
        logger.warning("Снимки не найдены. Оцениваем риск только по погоде.")
        return {
            "status": "ok",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "weather": weather,
            "risk_level": "medium",
            "risk_score": 0.5,
            "center_lat": lat,
            "center_lon": lon,
            "ndvi": None,
            "problem_areas": [],
        }

    ndvi_result = await ndvi_calculator.get_mean_ndvi(image_urls["red_url"], image_urls["nir_url"])
    if ndvi_result is None:
        logger.warning("NDVI вернул None.")
        return None

    try:
        current_month = datetime.now(timezone.utc).month
        risk_score, risk_level = predictor.predict_risk(
            weather_data=weather,
            ndvi_data=ndvi_result,
            current_month=current_month
        )
    except Exception:
        logger.error("Пайплайн аварийно завершен из-за ошибки инференса.")
        return None

    logger.info(f"Пайплайн успешно завершен. Score: {risk_score}, Level: {risk_level}")

    return {
        "status": "ok",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "weather": weather,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "center_lat": lat,
        "center_lon": lon,
        "ndvi": {
            "mean_ndvi": ndvi_result["mean_ndvi"],
            "total_risk_zones": ndvi_result["total_risk_zones"],
        },
        "problem_areas": ndvi_result["problem_areas"],
    }


async def _run_job(job_id: str, lat: float, lon: float):
    try:
        result = await _run_pipeline(lat, lon)
        if result is None:
            _jobs[job_id] = {"status": "failed", "error": "Pipeline returned no result"}
        else:
            _jobs[job_id] = {"status": "done", "result": result}
    except Exception:
        logger.error(f"Job {job_id} failed", exc_info=True)
        _jobs[job_id] = {"status": "failed", "error": "Unexpected error during analysis"}


async def _background_loop():
    global _latest_result, _pipeline_running
    while True:
        _pipeline_running = True
        logger.info("Запуск фонового цикла для Саратовской области...")
        try:
            result = await _run_pipeline(SARATOV_LAT, SARATOV_LON)
            if result:
                _latest_result = result
        except Exception:
            logger.error("Критическая ошибка в фоновом пайплайне", exc_info=True)
        _pipeline_running = False
        logger.info(f"Уход в спящий режим на {PIPELINE_INTERVAL} секунд.")
        await asyncio.sleep(PIPELINE_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    # Поднимаем модель строго при инициализации приложения
    predictor = FirePredictor(logger)

    asyncio.create_task(_background_loop())
    yield


app = FastAPI(title="Fire Predict API", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "pipeline_running": _pipeline_running}


@app.get("/predict")
async def predict():
    if _latest_result is None:
        return JSONResponse(
            status_code=503,
            content={"status": "pending", "message": "Pipeline has not completed its first run yet."},
        )
    return _latest_result


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running"}
    asyncio.create_task(_run_job(job_id, req.lat, req.lon))
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return job

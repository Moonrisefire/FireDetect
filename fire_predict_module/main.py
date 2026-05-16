import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.router import dummy_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("fire_predict_module")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Prediction in progress")
    yield
    # Закрытие при остановке
    log.info("Module task ended")

app = FastAPI(title="Fire predict NDVI service", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
    }

app.include_router(dummy_router, prefix="/api")
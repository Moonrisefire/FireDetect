from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.prediction import prediction_router
from .api.system import system_router
from .api.cv_analysis import cv_router

import uvicorn

from fastapi.middleware.cors import CORSMiddleware

import logging

from .services.database import SessionLocal, engine, Base
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="шашлыки")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешает запросы с любых адресов (для разработки)
    allow_credentials=True,
    allow_methods=["*"],  # Разрешает POST, GET и т.д.
    allow_headers=["*"],  # Разрешает отправлять файлы и JSON
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("fire_predict_module")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Упс! Балбесы на бэке опять что-то сломали.", "details": str(exc)},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prediction_router, prefix="/api/prediction")
app.include_router(system_router, prefix="/api/system")
app.include_router(cv_router, prefix="/api/cv")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

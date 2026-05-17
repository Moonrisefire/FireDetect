import logging
import uvicorn

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.system import system_router
from .api.cv_analysis import cv_router
from .api.risk import risk_router
from .services.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="шашлыки")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


app.include_router(system_router, prefix="/api/system")
app.include_router(cv_router, prefix="/api/cv")
app.include_router(risk_router, prefix="/api/risk")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

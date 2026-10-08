import logging
import uvicorn

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.system import system_router
from .api.cv_analysis import cv_router
from .api.risk import risk_router
from .services.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FireDetect")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Is-Fire", "X-Max-Confidence", "X-Frames-Seen", "X-Frames-Hit"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("fire_predict_module")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)
    log.error("Unhandled exception on %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )


app.include_router(system_router, prefix="/api/system")
app.include_router(cv_router, prefix="/api/cv")
app.include_router(risk_router, prefix="/api/risk")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

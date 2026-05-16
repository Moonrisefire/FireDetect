import os
from fastapi import APIRouter, UploadFile, File, HTTPException
import httpx
from ..schemas.schemas import DetectionResponse

detection_router = APIRouter()

PREDICTOR_URL = os.getenv(
    "FIRE_PREDICT_URL",
    "http://fire-predict-api:8001/predict"
)

@detection_router.post("/predict", response_model=DetectionResponse)
async def predict_fire(file: UploadFile = File(...)):
    contents = await file.read()
    files = {"file": (file.filename, contents, file.content_type or "application/octet-stream")}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(PREDICTOR_URL, files=files)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Prediction service unreachable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Prediction service error: {resp.status_code}")

    try:
        data = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Prediction service returned invalid JSON")

    return data
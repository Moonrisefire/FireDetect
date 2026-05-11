from fastapi import APIRouter, UploadFile, File
from .app.schemas.schemas import DetectionResponse

detection_router = APIRouter()

@detection_router.post("/predict", response_model=DetectionResponse)
async def predict_fire(file: UploadFile = File(...)):
    # тут вызывать модель

    mock_result = {
        "is_fire": True,
        "detections": [
            {
                "label": "fire",
                "confidence": 0.92,
                "x_min": 100, "y_min": 150, "x_max": 200, "y_max": 250
            }
        ]
    }

    return mock_result
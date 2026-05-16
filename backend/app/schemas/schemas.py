from pydantic import BaseModel
from typing import List, Optional

class DetectionBox(BaseModel):
    label: str
    confidence: float
    x_min: int
    y_min: int
    x_max: int
    y_max: int

class DetectionResponse(BaseModel):
    is_fire: bool
    detections: List[DetectionBox]

class RiskRequest(BaseModel):
    lat: float
    lon: float

class RiskResponse(BaseModel):
    risk_level: str  # Low, Medium, High
    score: float     # 0.0 - 1.0
    temp: float
    humidity: float

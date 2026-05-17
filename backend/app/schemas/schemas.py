from pydantic import BaseModel
from typing import Any, List, Optional

class DetectionBox(BaseModel):
    label: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float

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

class MarkerSchema(BaseModel):
    position: List[float]
    popup: str

class RiskEvaluateResponse(BaseModel):
    center: List[Optional[float]]
    risk_level: str
    score: int                        # 0–100
    temp: Optional[float]
    humidity: Optional[float]
    markers: List[MarkerSchema]
    polygons: List[List[List[float]]]

class AnalyzeResponse(BaseModel):
    job_id: str

class JobResponse(BaseModel):
    status: str                       # running | done | failed
    result: Optional[RiskEvaluateResponse] = None
    error: Optional[str] = None

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class BoundingBox(BaseModel):
    label: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DetectionResult(BaseModel):
    is_fire: bool
    confidence: float
    bounding_boxes: List[BoundingBox]


class DetectionLogBase(BaseModel):
    camera_id: Optional[int] = None
    filename: str
    is_fire: bool
    confidence: Optional[float] = None
    bounding_boxes: Optional[List[BoundingBox]] = None


class DetectionLogCreate(DetectionLogBase):
    pass


class DetectionLogResponse(DetectionLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class BoundingBox(BaseModel):
    class_name: str = Field(alias="class")
    confidence: float
    bbox: List[float]

class DetectionLogBase(BaseModel):
    camera_id: Optional[int] = None
    filename: str
    is_fire: bool
    confidence: Optional[float] = None
    bounding_boxes: Optional[List[BoundingBox]] = Field(default_factory=list)

class DetectionLogCreate(DetectionLogBase):
    pass

class DetectionLogResponse(DetectionLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
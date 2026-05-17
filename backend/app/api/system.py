from fastapi import APIRouter, Depends
import asyncio

from ..services.detection_client import health_check as detection_health
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..services.database import get_db, DetectionLog

system_router = APIRouter()

@system_router.get("/health")
async def health_check():
    # include detection_module health in aggregated health
    det = await detection_health()
    status = "ok" if det.get("ok", False) else "degraded"
    return {"status": status, "detection_module": det}

@system_router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_imgs = db.query(DetectionLog).count()
    
    # Считаем среднюю уверенность для всех найденных пожаров
    avg_conf = db.query(func.avg(DetectionLog.confidence)).filter(DetectionLog.is_fire == True).scalar()
    
    return {
        "imgs": total_imgs,
        "avg": round(avg_conf * 100, 2) if avg_conf else 0.0,
    }
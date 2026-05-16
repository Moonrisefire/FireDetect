from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..services.database import get_db, DetectionLog

system_router = APIRouter()

@system_router.get("/health")
def health_check():
    return {"status": "ok"}

@system_router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_imgs = db.query(DetectionLog).count()
    
    # Считаем среднюю уверенность для всех найденных пожаров
    avg_conf = db.query(func.avg(DetectionLog.confidence)).filter(DetectionLog.is_fire == True).scalar()
    
    return {
        "imgs": total_imgs,
        "avg": round(avg_conf, 2) if avg_conf else 0.0,
    }
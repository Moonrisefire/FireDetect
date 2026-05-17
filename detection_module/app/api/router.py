from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..utils.utils import get_logger
from ..db.database import get_db
from ..db import models, schemas
from ..cv_module.detector import WildfireDetector
from PIL import Image
import io

cv_router = APIRouter()

logger = get_logger("cv_analysis")

logger.info("Инициализация модуля CV")
MODEL_PATH = Path(__file__).resolve().parents[1] / "cv_module" / "weights" / "fire_model.pt"
detector = WildfireDetector(model_path=str(MODEL_PATH))

@cv_router.post("/detect/{camera_id}", response_model=schemas.DetectionResult)
async def detect_fire_from_camera(
    camera_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Проверяем наличие камеры в БД
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Камера не найдена в базе данных")

    # Анализируем изображение и возвращаем результат без записи в БД:
    # detection_logs принадлежит backend-модулю (см. data-ownership диаграмму).
    image_bytes = await file.read()
    return detector.analyze_image(image_bytes, conf_threshold=0.35)


# Полностью замени detect_fire_manual в router.py

@cv_router.post("/detect_manual")
def detect_fire_manual(file: UploadFile = File(...)): # УБРАЛИ async!
    logger.info(f"--- НАЧАЛО АНАЛИЗА: {file.filename} ---")

    # Читаем сырые байты СИНХРОННО
    image_bytes = file.file.read()

    logger.info("Байты прочитаны. Передаем в YOLO...")

    # Передаем байты (detector.py сам умеет делать из них картинку!)
    cv_result = detector.analyze_image(image_bytes, conf_threshold=0.35)

    logger.info("Анализ завершен!")

    return {
        "is_fire": cv_result["is_fire"],
        "detections": cv_result["bounding_boxes"]
    }

# чё-то с камерами короче
@cv_router.get("/cameras")
def get_all_cameras(db: Session = Depends(get_db)):
    return db.query(models.Camera).all()
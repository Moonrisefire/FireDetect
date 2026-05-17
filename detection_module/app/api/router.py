from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..utils.utils import get_logger
from ..db.database import get_db
from ..db import models, schemas
from ..cv_module.detector import WildfireDetector
from PIL import Image
import io
import tempfile
import os
import cv2
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks

cv_router = APIRouter()

logger = get_logger("cv_analysis")

logger.info("Инициализация модуля CV")
MODEL_PATH = Path(__file__).resolve().parents[1] / "cv_module" / "weights" / "fire_model.pt"
detector = WildfireDetector(model_path=str(MODEL_PATH))

@cv_router.post("/detect/{camera_id}", response_model=schemas.DetectionLogResponse)
async def detect_fire_from_camera(
    camera_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Проверяем наличие камеры в БД
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Камера не найдена в базе данных")

    # 2. Читаем картинку и отправляем
    image_bytes = await file.read()
    cv_result = detector.analyze_image(image_bytes, conf_threshold=0.35)

    # 3. Сохраняем результат в базу данных
    db_log = models.DetectionLog(
        camera_id=camera_id,
        filename=file.filename,
        is_fire=cv_result["is_fire"],
        confidence=cv_result["confidence"],
        bounding_boxes=cv_result["bounding_boxes"]
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)

    return db_log

@cv_router.post("/detect_manual")
def detect_fire_manual(file: UploadFile = File(...)): # УБРАЛИ async!
    logger.info(f"--- НАЧАЛО АНАЛИЗА: {file.filename} ---")

    # Читаем сырые байты
    image_bytes = file.file.read()

    logger.info("Байты прочитаны. Передаем в YOLO...")

    # Передаем байты 
    cv_result = detector.analyze_image(image_bytes, conf_threshold=0.35)

    logger.info("Анализ завершен!")

    return {
        "is_fire": cv_result["is_fire"],
        "detections": cv_result["bounding_boxes"]
    }


def cleanup_temp_file(path: str):
    """Удаляет временный файл после отправки пользователю"""
    if os.path.exists(path):
        os.remove(path)


@cv_router.post("/detect_video")
def detect_fire_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    logger.info(f"--- НАЧАЛО АНАЛИЗА ВИДЕО: {file.filename} ---")

    # 1. Сохраняем загруженное видео во временный файл
    in_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    in_temp.write(file.file.read())
    in_temp.close()

    # 2. Создаем файл для готового видео
    out_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    out_path = out_temp.name
    out_temp.close()

    # 3. Настраиваем OpenCV для покадрового чтения
    cap = cv2.VideoCapture(in_temp.name)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Кодек VP80 идеально работает в браузерах
    fourcc = cv2.VideoWriter_fourcc(*'VP80')
    out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    # 4. Прогоняем каждый кадр через нейросеть
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # YOLO находит объекты
        results = detector.model.predict(frame, conf=0.35, verbose=False)

        # Магия: YOLO сама рисует рамки на кадре!
        annotated_frame = results[0].plot()

        # Записываем кадр в новое видео
        out.write(annotated_frame)

    # 5. Закрываем файлы и удаляем исходник
    cap.release()
    out.release()
    os.remove(in_temp.name)

    logger.info("Видео успешно обработано!")

    # 6. Возвращаем видео и даем команду удалить его с жесткого диска после отправки
    background_tasks.add_task(cleanup_temp_file, out_path)
    return FileResponse(out_path, media_type="video/webm")

# чё-то с камерами короче
@cv_router.get("/cameras")
def get_all_cameras(db: Session = Depends(get_db)):
    return db.query(models.Camera).all()

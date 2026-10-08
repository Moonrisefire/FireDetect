from pathlib import Path
import os
import tempfile

import cv2
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..cv_module.detector import WildfireDetector
from ..cv_module.image_io import ImageDecodeError
from ..db import models, schemas
from ..db.database import get_db
from ..utils.utils import get_logger

cv_router = APIRouter()

logger = get_logger("cv_analysis")

logger.info("Инициализация модуля CV")
MODEL_PATH = Path(__file__).resolve().parents[1] / "cv_module" / "weights" / "fire_model.pt"
detector = WildfireDetector(model_path=str(MODEL_PATH))

MAX_UPLOAD_BYTES = 80 * 1024 * 1024
FRAME_STRIDE = 5
MAX_INFERENCES = 300


def _reject_if_too_large(raw: bytes) -> None:
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 80 MB")


def _analyze_or_422(image_bytes: bytes) -> dict:
    try:
        return detector.analyze_image(image_bytes, conf_threshold=0.35)
    except ImageDecodeError as exc:
        raise HTTPException(status_code=422, detail="Cannot read image") from exc


def cleanup_temp_file(path: str):
    if os.path.exists(path):
        os.remove(path)


@cv_router.post("/detect/{camera_id}", response_model=schemas.DetectionResult)
async def detect_fire_from_camera(
    camera_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Камера не найдена в базе данных")

    image_bytes = await file.read()
    _reject_if_too_large(image_bytes)
    return _analyze_or_422(image_bytes)


@cv_router.post("/detect_manual")
def detect_fire_manual(file: UploadFile = File(...)):
    logger.info(f"--- НАЧАЛО АНАЛИЗА: {file.filename} ---")
    image_bytes = file.file.read()
    _reject_if_too_large(image_bytes)
    cv_result = _analyze_or_422(image_bytes)
    logger.info("Анализ завершен!")
    return {
        "is_fire": cv_result["is_fire"],
        "detections": cv_result["bounding_boxes"]
    }


def _frame_confidence(result) -> tuple[bool, float]:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return False, 0.0
    confidences = [float(box.conf[0]) for box in boxes]
    return True, max(confidences)


@cv_router.post("/detect_video")
def detect_fire_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    logger.info(f"--- НАЧАЛО АНАЛИЗА ВИДЕО: {file.filename} ---")
    raw = file.file.read()
    _reject_if_too_large(raw)
    if not raw:
        raise HTTPException(status_code=422, detail="Cannot read video")

    in_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    in_temp.write(raw)
    in_temp.close()

    out_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    out_path = out_temp.name
    out_temp.close()

    cap = cv2.VideoCapture(in_temp.name)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    if not cap.isOpened() or width <= 0 or height <= 0:
        cap.release()
        cleanup_temp_file(in_temp.name)
        cleanup_temp_file(out_path)
        raise HTTPException(status_code=422, detail="Cannot read video")
    if fps < 1:
        fps = 25.0

    fourcc = cv2.VideoWriter_fourcc(*"VP80")
    out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
    if not out.isOpened():
        cap.release()
        cleanup_temp_file(in_temp.name)
        cleanup_temp_file(out_path)
        raise HTTPException(status_code=500, detail="Cannot encode video")

    frames_seen = 0
    frames_hit = 0
    inferences = 0
    max_confidence = 0.0
    annotated = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frames_seen % FRAME_STRIDE == 0:
            if inferences >= MAX_INFERENCES:
                break
            results = detector.model.predict(frame, conf=0.35, verbose=False)
            inferences += 1
            annotated = results[0].plot()
            hit, conf = _frame_confidence(results[0])
            if hit:
                frames_hit += 1
                max_confidence = max(max_confidence, conf)
        if annotated is None:
            annotated = frame
        out.write(annotated)
        frames_seen += 1

    cap.release()
    out.release()
    os.remove(in_temp.name)

    logger.info("Видео успешно обработано!")
    background_tasks.add_task(cleanup_temp_file, out_path)
    headers = {
        "X-Is-Fire": "true" if frames_hit else "false",
        "X-Max-Confidence": f"{max_confidence:.4f}",
        "X-Frames-Seen": str(frames_seen),
        "X-Frames-Hit": str(frames_hit),
    }
    return FileResponse(out_path, media_type="video/webm", headers=headers)


@cv_router.get("/cameras")
def get_all_cameras(db: Session = Depends(get_db)):
    return db.query(models.Camera).all()

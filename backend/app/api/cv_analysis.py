from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from ..schemas.schemas import DetectionResponse
from ..services.detection_client import detect_image, detect_image_manual, detect_video, list_cameras
from ..services.database import get_db, DetectionLog

MAX_UPLOAD_BYTES = 80 * 1024 * 1024

cv_router = APIRouter()


@cv_router.post("/detect", response_model=DetectionResponse)
async def detect_from_camera(
    file: UploadFile = File(...),
    camera_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Proxy endpoint: accepts image and required `camera_id`, forwards to detection_module,
    persists a DetectionLog row in the backend DB, and returns the mapped response.
    """
    contents = await file.read()

    try:
        det = await detect_image(file.filename, contents, file.content_type or "application/octet-stream", camera_id=camera_id)
    except HTTPException as e:
        raise e

    # detection_module emits {label, confidence, x_min, y_min, x_max, y_max} — pass through.
    boxes = det.get("bounding_boxes") or []

    is_fire = bool(det.get("is_fire", False))
    overall_conf = float(det.get("confidence", 0.0) or 0.0)

    log = DetectionLog(
        camera_id=camera_id,
        filename=file.filename,
        is_fire=is_fire,
        confidence=overall_conf,
        bounding_boxes=boxes,
    )
    db.add(log)
    db.commit()

    return {"is_fire": is_fire, "detections": boxes}


@cv_router.post("/detect_manual")
async def detect_manual(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    try:
        det = await detect_image_manual(file.filename, contents, file.content_type or "application/octet-stream")
    except HTTPException as e:
        raise e

    boxes = det.get("detections") or []
    is_fire = bool(det.get("is_fire", False))
    conf = (sum(b.get("confidence", 0.0) for b in boxes) / len(boxes)) if boxes else 0.0

    log = DetectionLog(
        camera_id=None,
        filename=file.filename,
        is_fire=is_fire,
        confidence=conf,
        bounding_boxes=boxes,
    )
    db.add(log)
    db.commit()

    return {"is_fire": is_fire, "detections": boxes}


@cv_router.post("/detect_video")
async def detect_video_proxy(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 80 MB")

    resp = await detect_video(file.filename or "video", contents, file.content_type or "application/octet-stream")
    if resp.status_code == 413:
        raise HTTPException(status_code=413, detail="File is larger than 80 MB")
    if resp.status_code == 422:
        raise HTTPException(status_code=422, detail="Cannot read video")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Detection service error: {resp.status_code}")

    is_fire = (resp.headers.get("x-is-fire") or "false").lower() == "true"
    try:
        confidence = float(resp.headers.get("x-max-confidence") or 0.0)
    except ValueError:
        confidence = 0.0

    log = DetectionLog(
        camera_id=None,
        filename=file.filename,
        is_fire=is_fire,
        confidence=confidence,
        bounding_boxes=[],
    )
    db.add(log)
    db.commit()

    forwarded = {
        "X-Is-Fire": resp.headers.get("x-is-fire", "false"),
        "X-Max-Confidence": resp.headers.get("x-max-confidence", "0"),
        "X-Frames-Seen": resp.headers.get("x-frames-seen", "0"),
        "X-Frames-Hit": resp.headers.get("x-frames-hit", "0"),
    }
    media_type = resp.headers.get("content-type", "video/webm")
    return Response(content=resp.content, media_type=media_type, headers=forwarded)


@cv_router.get("/cameras")
async def get_cameras():
    """Return the camera catalog. Cameras are owned by detection_module's DB; we proxy."""
    return await list_cameras()


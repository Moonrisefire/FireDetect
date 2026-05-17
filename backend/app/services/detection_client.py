import os
import asyncio
from typing import Optional, Dict, Any

import httpx
from fastapi import HTTPException

DETECTION_BASE = os.getenv("DETECTION_URL", "http://detection_module:8080")


async def _post_with_retries(url: str, files: dict, timeout: float = 10.0, retries: int = 3) -> httpx.Response:
    backoff = 0.1
    for attempt in range(1, retries + 1):
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(url, files=files)
                return resp
            except httpx.RequestError as e:
                if attempt == retries:
                    raise HTTPException(status_code=502, detail=f"Detection service unreachable: {e}")
                await asyncio.sleep(backoff)
                backoff *= 2


async def detect_image(filename: str, contents: bytes, content_type: str, camera_id: int) -> Dict[str, Any]:
    """Send image bytes to detection_module for a specific camera via /api/detect/{camera_id}.

    `camera_id` is required because detection_module exposes only camera-specific endpoint.
    Raises HTTPException on errors.
    """
    files = {"file": (filename, contents, content_type or "application/octet-stream")}

    url = f"{DETECTION_BASE}/api/detect/{camera_id}"

    resp = await _post_with_retries(url, files=files, timeout=20.0)

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Camera not found in detection module")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Detection service error: {resp.status_code}")

    try:
        return resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Detection service returned invalid JSON")


async def health_check() -> Dict[str, Any]:
    # detection_module exposes root '/' for status; use that for a lightweight health check
    url = f"{DETECTION_BASE}/"
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(url)
        except httpx.RequestError as e:
            return {"ok": False, "detail": str(e)}

    if resp.status_code != 200:
        return {"ok": False, "detail": f"status {resp.status_code}"}

    try:
        return {"ok": True, "detail": resp.json()}
    except ValueError:
        return {"ok": True, "detail": "non-json-response"}


async def detect_image_manual(filename: str, contents: bytes, content_type: str) -> Dict[str, Any]:
    """Send image bytes to detection_module's /detect_manual (no camera required)."""
    files = {"file": (filename, contents, content_type or "application/octet-stream")}
    url = f"{DETECTION_BASE}/api/detect_manual"
    resp = await _post_with_retries(url, files=files, timeout=20.0)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Detection service error: {resp.status_code}")
    try:
        return resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Detection service returned invalid JSON")


async def list_cameras() -> list:
    """Fetch the camera catalog from detection_module.

    Cameras live in detection_module's DB per the data-ownership diagram; the backend
    proxies reads instead of duplicating the table.
    """
    url = f"{DETECTION_BASE}/api/cameras"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Detection service unreachable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Detection service error: {resp.status_code}")

    try:
        return resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Detection service returned invalid JSON")

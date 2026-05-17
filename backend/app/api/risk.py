import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException
from ..schemas.schemas import RiskRequest, RiskEvaluateResponse, AnalyzeResponse, JobResponse

FIRE_PREDICT_BASE = os.getenv("FIRE_PREDICT_BASE_URL", "http://fire_predict_api:8001")

risk_router = APIRouter()


def _map_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    weather = raw.get("weather") or {}
    problem_areas = raw.get("problem_areas") or []

    markers = [
        {
            "position": [area["center_lat"], area["center_lon"]],
            "popup": f"Risk zone ({area.get('cluster_size_pixels', '?')} px)",
        }
        for area in problem_areas
    ]

    polygons = [
        [[pt["lat"], pt["lon"]] for pt in area.get("polygon", [])]
        for area in problem_areas
        if area.get("polygon")
    ]

    return {
        "center": [raw.get("center_lat"), raw.get("center_lon")],
        "risk_level": (raw.get("risk_level") or "unknown").capitalize(),
        "score": round((raw.get("risk_score") or 0.0) * 100),
        "temp": weather.get("temperature"),
        "humidity": weather.get("humidity"),
        "markers": markers,
        "polygons": polygons,
    }


@risk_router.post("/evaluate", response_model=RiskEvaluateResponse)
async def evaluate(_: RiskRequest):
    url = f"{FIRE_PREDICT_BASE}/predict"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Fire predict service unreachable: {e}")

    if resp.status_code == 503:
        raise HTTPException(status_code=503, detail="Fire predict pipeline has not completed its first run yet.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Fire predict service error: {resp.status_code}")

    try:
        raw = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Fire predict service returned invalid JSON")

    return _map_response(raw)


@risk_router.post("/analyze", response_model=AnalyzeResponse)
async def start_analysis(data: RiskRequest):
    url = f"{FIRE_PREDICT_BASE}/analyze"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"lat": data.lat, "lon": data.lon})
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Fire predict service unreachable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Fire predict service error: {resp.status_code}")

    return resp.json()


@risk_router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    url = f"{FIRE_PREDICT_BASE}/jobs/{job_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Fire predict service unreachable: {e}")

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Job not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Fire predict service error: {resp.status_code}")

    try:
        job = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Fire predict service returned invalid JSON")

    if job.get("status") == "done" and job.get("result"):
        return {"status": "done", "result": _map_response(job["result"])}

    return job

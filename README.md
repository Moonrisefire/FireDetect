# FireDetect

A microservice system for real-time fire and smoke detection from images/video, and satellite-based wildfire risk prediction on an interactive map.

---

## Main Idea

FireDetect combines two AI capabilities in one web application:

1. **Fire Detection** — upload an image or video and get instant fire/smoke detection results powered by a YOLOv8 model, with bounding boxes drawn around detected objects.
2. **Fire Risk Prediction** — click anywhere on a map and get a wildfire risk assessment for that area based on real satellite imagery (Sentinel-2 NDVI analysis), current weather data, and ML-based risk scoring.

The system is built as four independent microservices orchestrated via Docker Compose: a React frontend, a FastAPI backend (API gateway + database), a YOLO detection service, and a satellite prediction service.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│              React + Vite frontend (:5173)              │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────┐
│            Backend — API Gateway (:8000)                │
│         FastAPI · SQLAlchemy · SQLite                   │
│    /api/system   /api/cv   /api/risk                    │
└────────────┬─────────────────────────┬──────────────────┘
             │ HTTP                    │ HTTP
┌────────────▼────────────┐ ┌─────────▼──────────────────┐
│  detection_module        │ │  fire_predict_module        │
│  FastAPI + YOLOv8 (:8080)│ │  FastAPI + Sentinel-2      │
│  /api/detect_manual      │ │  /analyze  /predict        │
│  /api/detect/{camera_id} │ │  /jobs/{job_id}            │
│  /api/detect_video       │ │                            │
└──────────────────────────┘ └────────────────────────────┘
                                  │           │          │
                            Open-Meteo   AWS STAC    NDVI+DBSCAN
                            (weather)  (Sentinel-2) (risk zones)
```

---

## Services & Endpoints

### Backend (`localhost:8000`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/system/health` | Aggregated health — checks detection_module liveness |
| GET | `/api/system/stats` | Total images analyzed + average fire-detection confidence |
| POST | `/api/cv/detect` | Detect fire from a named camera (requires `camera_id`) |
| POST | `/api/cv/detect_manual` | Detect fire in a manually uploaded image |
| GET | `/api/cv/cameras` | List all registered cameras from detection_module |
| POST | `/api/risk/evaluate` | Return the latest cached satellite risk result |
| POST | `/api/risk/analyze` | Start async risk analysis for a given `lat`/`lon` |
| GET | `/api/risk/jobs/{job_id}` | Poll job status (`running` / `done` / `failed`) |

### Detection Module (`localhost:8080`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Service status and docs link |
| POST | `/api/detect/{camera_id}` | Detect fire in image tied to a camera record |
| POST | `/api/detect_manual` | Detect fire in an uploaded image (no camera required) |
| POST | `/api/detect_video` | Process video, returns annotated WebM with bounding boxes |
| GET | `/api/cameras` | List cameras from the detection module database |

### Fire Predict Module (`localhost:8001`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check + pipeline running flag |
| GET | `/predict` | Return latest cached prediction result (503 if not ready) |
| POST | `/analyze` | Start async risk analysis for body `{lat, lon}` |
| GET | `/jobs/{job_id}` | Poll async job status and result |

### Frontend (`localhost:5173`)

| Page | Route | Purpose |
|------|-------|---------|
| Home | `/` | Dashboard with system stats |
| Detection | `/detection` | Upload image/video, view fire detection results |
| Prediction | `/prediction` | Interactive map with satellite risk prediction |

---

## How to Launch Locally

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Moonrisefire/FireDetect.git
cd FireDetect

# 2. Build and start all services
docker compose up --build

# 3. Open the app
#    Frontend:          http://localhost:5173
#    Backend API docs:  http://localhost:8000/docs
#    Detection docs:    http://localhost:8080/docs
#    Prediction docs:   http://localhost:8001/docs
```

The first startup takes a few minutes because Docker needs to build images and the detection module needs to download/load the YOLO model weights (`fire_model.pt`).

To stop all services:

```bash
docker compose down
```

---

## Pipelines — How It Works End to End

### Pipeline 1: Fire Detection on an Uploaded Image

**Trigger:** User opens the Detection page, selects an image file, and clicks "Detect".

```
User clicks "Detect"
       │
       ▼
[Frontend — DetectionPage.jsx]
POST http://localhost:8000/api/cv/detect_manual
  Body: FormData { file: <image> }
       │
       ▼
[Backend — cv_analysis.py → detect_manual()]
  1. Receives the uploaded image file
  2. Forwards it via httpx to:
       POST http://detection_module:8080/api/detect_manual
  3. Retry logic: up to 3 attempts (exponential backoff 0.1s → 0.4s)
       │
       ▼
[Detection Module — router.py → detect_fire_manual()]
  1. Reads uploaded image bytes
  2. Converts to RGB PIL Image
  3. Runs WildfireDetector.detect():
       - Feeds image to YOLOv8 model (fire_model.pt)
       - Confidence threshold: 0.35
       - Detects classes: Fire, Smoke
       - Extracts bounding boxes (x_min, y_min, x_max, y_max, label, confidence)
       - Tracks max confidence across all detections
  4. Returns:
       { is_fire: bool, confidence: float, bounding_boxes: [...] }
       │
       ▼
[Backend — cv_analysis.py continued]
  4. Saves result to DetectionLog table in SQLite:
       { camera_id: null, filename, is_fire, confidence, bounding_boxes, timestamp }
  5. Returns response to frontend:
       { is_fire: bool, detections: [{ label, confidence, x_min, y_min, x_max, y_max }] }
       │
       ▼
[Frontend — DetectionPage.jsx]
  6. Renders the uploaded image
  7. Draws bounding boxes as colored overlays on the image canvas
  8. Displays labels (Fire / Smoke) with confidence percentages
  9. Appends result to local detection history (localStorage via cache.js)
```

**Result:** User sees the image with boxes drawn around detected fire/smoke regions and a fire/no-fire verdict.

---

### Pipeline 2: Wildfire Risk Prediction on the Map

**Trigger:** User opens the Prediction page, pans the map to a location, and clicks "Make Forecast" (Сделать прогноз).

```
User clicks "Make Forecast"
       │
       ▼
[Frontend — PredictionPage.jsx]
POST http://localhost:8000/api/risk/analyze
  Body: { lat: <map center lat>, lon: <map center lon> }
       │
       ▼
[Backend — risk.py → start_analysis()]
  1. Receives lat/lon
  2. Forwards to fire_predict_module:
       POST http://fire_predict_api:8001/analyze
       Body: { lat, lon }
  3. Gets back { job_id: "<UUID>" }
  4. Returns job_id to frontend
       │
       ▼
[Fire Predict Module — main.py → analyze()]
  1. Generates a UUID job_id
  2. Spawns asyncio background task for this job
  3. Returns { job_id } immediately (non-blocking)

  [Background Task — run_pipeline(lat, lon, job_id)]
  Step A — Weather Check (WeatherClient)
    • Calls Open-Meteo API for current conditions at lat/lon:
        temperature, humidity, precipitation, wind_speed
    • Early exit: if precipitation > 1.0mm OR temperature < 5°C → risk_level = "low", skip satellite
    
  Step B — Satellite Imagery (SatelliteClient)
    • Queries AWS Element84 STAC API:
        collection: sentinel-2-l2a
        date range: last 30 days
        cloud cover: < 30%
        bbox: ±0.5° around the requested point
    • Picks most recent scene
    • Returns direct S3 download URLs for the Red band and NIR band

  Step C — NDVI Calculation (NDVICalculator)
    • Downloads Red + NIR band rasters from S3
    • Computes NDVI = (NIR − RED) / (NIR + RED + ε) per pixel
    • Identifies dry vegetation: pixels where 0.15 < NDVI < 0.25
    • Runs DBSCAN clustering (eps=5px, min_samples=10) to group dry pixels into zones
    • For each cluster:
        - Computes convex hull polygon (converted to WGS84 lat/lon)
        - Finds geographic center
        - Records cluster size in pixels
    • Saves debug visualization to /app/ndvi_clusters.png
    
  Step D — Risk Scoring
    • ndvi_score   = max(0, 1 − |mean_ndvi − 0.20| / 0.20)
    • temp_score   = clamp((temperature − 20) / 20, 0, 1)
    • humidity_score = clamp((60 − humidity) / 60, 0, 1)
    • risk_score   = 0.5 × ndvi_score + 0.25 × temp_score + 0.25 × humidity_score
    • risk_level:
        < 0.35  → "low"
        < 0.65  → "medium"
        ≥ 0.65  → "high"
    
  Step E — Store Result
    • Writes full result to _jobs[job_id]:
        { status: "done", result: { risk_level, risk_score, weather, ndvi,
          center_lat, center_lon, problem_areas: [{ center, polygon, cluster_size }] } }
       │
       ▼
[Frontend — PredictionPage.jsx polls every 3 seconds]
GET http://localhost:8000/api/risk/jobs/{job_id}
       │
       ▼
[Backend — risk.py → get_job()]
  Proxies to: GET http://fire_predict_api:8001/jobs/{job_id}
  Returns: { status: "running"|"done"|"failed", result?, error? }
       │
       ▼
  When status = "done":
[Frontend — PredictionPage.jsx]
  1. Stops polling
  2. Displays risk level badge (low / medium / high) with color coding
  3. Shows temperature and humidity from the weather snapshot
  4. Renders problem areas on the Leaflet map:
       - Red semi-transparent polygons for each dry vegetation cluster
       - Blue marker dots at cluster centers with info popups
```

**Result:** User sees the map overlaid with satellite-derived fire risk zones colored by danger level, plus weather conditions and a numeric risk score.

---

### Bonus Pipeline: Video Fire Detection

**Trigger:** User uploads a video file on the Detection page.

```
User selects a video file and clicks "Detect"
       │
       ▼
[Frontend — DetectionPage.jsx]
POST http://localhost:8080/api/detect_video   ← direct to detection_module (bypasses backend)
  Body: FormData { file: <video> }
       │
       ▼
[Detection Module — router.py → detect_fire_video()]
  1. Saves uploaded video to a temp file
  2. Opens with OpenCV VideoCapture
  3. For each frame:
       - Runs YOLO inference
       - Draws bounding boxes + labels on frame with OpenCV
  4. Encodes output with VP80 codec (WebM — browser compatible)
  5. Returns annotated video as FileResponse (binary blob)
       │
       ▼
[Frontend — DetectionPage.jsx]
  6. Receives binary blob
  7. Creates object URL: URL.createObjectURL(blob)
  8. Renders result in a <video> player element
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, React Router, Leaflet / React-Leaflet, Vite |
| Backend | FastAPI, SQLAlchemy 2, SQLite, httpx |
| Detection | FastAPI, YOLOv8 (ultralytics), Pillow, OpenCV |
| Prediction | FastAPI, aiohttp, rasterio, scikit-learn (DBSCAN), numpy, CatBoost|
| External APIs | Open-Meteo (weather), AWS Element84 STAC (Sentinel-2 satellite) |
| Infrastructure | Docker, Docker Compose |

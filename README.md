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
| POST | `/api/cv/detect_video` | Detect fire in an uploaded video and return an annotated WebM |
| GET | `/api/cv/cameras` | List registered cameras. Not used by the web UI |
| POST | `/api/risk/evaluate` | Return the cached forecast when the point lies inside its area. Otherwise 404 |
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

Camera routes are not used by the web UI. The product path is an uploaded image or video.

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

The first startup takes a few minutes because Docker builds the images and the detection module loads the YOLO weights shipped in the repository (`fire_model.pt`).

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

  [Background Task — run_pipeline(lat, lon)]
  Step A — Weather (WeatherClient)
    • Open-Meteo forecast API, daily fields, timezone Europe/Moscow
    • past 30 days plus today
    • Model features are the last 5 daily values:
        mean temperature_2m_max, max wind_speed_10m_max,
        sum of precipitation_sum, mean shortwave_radiation_sum,
        mean vapor_pressure_deficit_max, mean soil_moisture_0_to_7cm_mean
    • days_without_rain walks the whole daily series from the latest day
    • No weather → job failed. Rain or cold does not skip the model

  Step B — Satellite Imagery (SatelliteClient)
    • AWS Element84 STAC, collection sentinel-2-l2a
    • last 30 days, cloud cover below 20%
    • scene that contains the clicked point
    • URLs for the Red and NIR bands of that full scene

  Step C — NDVI (NDVICalculator)
    • mean_ndvi and dry_area_fraction are computed on the whole scene
    • dry pixels are 0.15 < NDVI < 0.25, then a 3×3 opening
    • DBSCAN polygons are limited to ±0.25° around the click and are not model features
    • If no scene is found, both NDVI features are 0 and the model still runs

  Step D — CatBoost
    • The ten features above, in the training order
    • risk_level: below 0.4992 low, below 0.75 medium, otherwise high
    • 0.4992 is the F1 threshold from training. 0.75 is only the map split

  Step E — Store Result
    • One analysis at a time
    • Finished jobs are kept up to about 50
    • A new map result replaces the previous polygons

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
POST http://localhost:8000/api/cv/detect_video
  Body: FormData { file: <video> }
       │
       ▼
[Backend — cv_analysis.py]
  Forwards the file to detection_module and stores the verdict from response headers
       │
       ▼
[Detection Module — router.py → detect_fire_video()]
  1. Rejects uploads larger than 80 MB and unreadable video with 422
  2. Runs YOLO on every 5th frame, at most 300 inferences
  3. Draws boxes and repeats them on the skipped frames
  4. Returns WebM plus X-Is-Fire, X-Max-Confidence, X-Frames-Seen, X-Frames-Hit
       │
       ▼
[Frontend — DetectionPage.jsx]
  Plays the annotated video and writes the real fire verdict into local history
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

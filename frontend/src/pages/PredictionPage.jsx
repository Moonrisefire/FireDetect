import { useEffect, useRef, useState, useCallback } from 'react'
import { MapContainer, TileLayer, Polygon, CircleMarker, Popup, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { fetchPrediction, startAnalysis, pollJob } from '../services/api'

const POLYGON_STYLE = { color: '#e00', weight: 2, fillColor: '#e00', fillOpacity: 0.15 }
const DOT_STYLE = { radius: 5, color: '#1447e6', fillColor: '#1447e6', fillOpacity: 0.85, weight: 1 }
const SARATOV = [51.5335, 45.9341]

function MapCenterTracker({ onMove }) {
  useMapEvents({ moveend: (e) => onMove(e.target.getCenter()) })
  return null
}

function PredictionPage() {
  const [latestStats, setLatestStats] = useState(null)
  const [allPolygons, setAllPolygons] = useState([])
  const [allMarkers, setAllMarkers] = useState([])
  const [analyzing, setAnalyzing] = useState(false)
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const currentCenter = useRef({ lat: SARATOV[0], lng: SARATOV[1] })
  const mountedRef = useRef(true)

  useEffect(() => {
    return () => { mountedRef.current = false }
  }, [])

  useEffect(() => {
    fetchPrediction()
      .then(data => {
        if (!mountedRef.current) return
        setLatestStats(data)
        setAllPolygons(data.polygons || [])
        setAllMarkers(data.markers || [])
      })
      .catch(() => {
        if (!mountedRef.current) return
        setStatus('Кэшированный прогноз недоступен. Нажми «Сделать прогноз» для анализа региона.')
      })
      .finally(() => {
        if (mountedRef.current) setLoading(false)
      })
  }, [])

  const handleAnalyze = useCallback(async () => {
    setAnalyzing(true)
    setStatus('Запускаем анализ…')

    const { lat, lng } = currentCenter.current

    try {
      const { job_id } = await startAnalysis(lat, lng)

      const poll = async () => {
        if (!mountedRef.current) return
        try {
          const job = await pollJob(job_id)
          if (job.status === 'done') {
            const result = job.result
            setLatestStats(result)
            setAllPolygons(prev => [...prev, ...result.polygons])
            setAllMarkers(prev => [...prev, ...result.markers])
            setStatus(`Готово. Найдено ${result.polygons.length} зон риска.`)
            setAnalyzing(false)
          } else if (job.status === 'failed') {
            setStatus(`Ошибка анализа: ${job.error || 'неизвестная ошибка'}`)
            setAnalyzing(false)
          } else {
            setTimeout(poll, 3000)
          }
        } catch {
          setStatus('Не удалось получить статус задачи.')
          setAnalyzing(false)
        }
      }

      setTimeout(poll, 3000)
    } catch {
      setStatus('Не удалось запустить анализ. Проверь соединение с сервером.')
      setAnalyzing(false)
    }
  }, [])

  return (
    <div className="prediction-page">
      <div className="page-header">
        <div>
          <h1>Прогноз</h1>
          <p>Прокрути карту до нужного региона и нажми «Сделать прогноз».</p>
        </div>
      </div>

      <div className="prediction-grid">
        <div className="card risk-panel">
          <h2>Результаты прогноза</h2>

          {loading ? (
            <div className="status-pill" style={{ marginTop: 18 }}>Загрузка…</div>
          ) : (
            <>
              {latestStats && (
                <div className="risk-details">
                  <div>
                    <span className="stat-label">Уровень риска</span>
                    <strong>{latestStats.risk_level}</strong>
                  </div>
                  <div>
                    <span className="stat-label">Оценка</span>
                    <strong>{latestStats.score.toFixed(0)}%</strong>
                  </div>
                  <div>
                    <span className="stat-label">Температура</span>
                    <strong>{latestStats.temp ?? '—'}°C</strong>
                  </div>
                  <div>
                    <span className="stat-label">Влажность</span>
                    <strong>{latestStats.humidity ?? '—'}%</strong>
                  </div>
                  <div>
                    <span className="stat-label">Зон риска на карте</span>
                    <strong>{allPolygons.length}</strong>
                  </div>
                </div>
              )}

              <button
                className="button button-primary"
                style={{ marginTop: 20, width: '100%' }}
                onClick={handleAnalyze}
                disabled={analyzing}
              >
                {analyzing ? 'Анализируем…' : 'Сделать прогноз'}
              </button>

              {status && (
                <div
                  className={`status-pill ${status.startsWith('Ошибка') || status.startsWith('Не удалось') ? 'status-error' : ''}`}
                  style={{ marginTop: 12 }}
                >
                  {status}
                </div>
              )}
            </>
          )}
        </div>

        <div className="map-card card">
          <MapContainer center={SARATOV} zoom={10} scrollWheelZoom={true} className="risk-map">
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <MapCenterTracker onMove={(c) => { currentCenter.current = c }} />
            {allPolygons.map((polygon, i) =>
              polygon.length > 0 && (
                <Polygon key={i} positions={polygon} pathOptions={POLYGON_STYLE} />
              )
            )}
            {allMarkers.map((marker, i) => (
              <CircleMarker key={i} center={marker.position} pathOptions={DOT_STYLE}>
                <Popup>{marker.popup}</Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      </div>
    </div>
  )
}

export default PredictionPage

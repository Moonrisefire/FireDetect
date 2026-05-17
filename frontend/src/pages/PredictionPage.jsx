import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polygon } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { fetchPrediction } from '../services/api'

const iconUrl = new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href
const iconRetinaUrl = new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href
const shadowUrl = new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href

const defaultIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})

L.Marker.prototype.options.icon = defaultIcon

const sampleData = {
  center: [37.7749, -122.4194],
  risk: 'Medium',
  score: 62,
  temperature: 29,
  humidity: 38,
  polygons: [
    [
      [37.783, -122.433],
      [37.783, -122.41],
      [37.77, -122.41],
      [37.77, -122.433],
    ],
  ],
  markers: [
    { position: [37.775, -122.42], popup: 'Predicted risk area' },
  ],
}

function PredictionPage() {
  const [prediction, setPrediction] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadPrediction() {
      try {
        const data = await fetchPrediction()
        setPrediction(data)
      } catch (err) {
        setError('Prediction API is not available yet. Showing sample risk zones.')
        setPrediction(sampleData)
      } finally {
        setLoading(false)
      }
    }

    loadPrediction()
  }, [])

  const mapCenter = prediction?.center ?? sampleData.center

  return (
    <div className="prediction-page">
      <div className="page-header">
        <div>
          <h1>Прогноз</h1>
          <p>Изучай зоны риска возникновения пожара на карте.</p>
        </div>
      </div>

      <div className="prediction-grid">
        <div className="card risk-panel">
          <h2>Результаты прогноза</h2>
          {loading ? (
            <div className="status-pill">Загрузка…</div>
          ) : (
            <>
              {error && <div className="status-pill status-error">{error}</div>}
              <div className="risk-details">
                <div>
                  <span className="stat-label">Уровень риска</span>
                  <strong>{prediction?.risk_level ?? sampleData.risk}</strong>
                </div>
                <div>
                  <span className="stat-label">Оценка</span>
                  <strong>{(prediction?.score ?? sampleData.score / 100).toFixed(0)}</strong>
                </div>
                <div>
                  <span className="stat-label">Температура</span>
                  <strong>{prediction?.temp ?? sampleData.temperature}°C</strong>
                </div>
                <div>
                  <span className="stat-label">Влажность</span>
                  <strong>{prediction?.humidity ?? sampleData.humidity}%</strong>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="map-card card">
          <MapContainer center={mapCenter} zoom={12} scrollWheelZoom={false} className="risk-map">
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {(prediction?.markers ?? sampleData.markers).map((marker, index) => (
              <Marker key={index} position={marker.position}>
                <Popup>{marker.popup}</Popup>
              </Marker>
            ))}
            {(prediction?.polygons ?? sampleData.polygons).map((polygon, index) => (
              <Polygon key={index} positions={polygon} pathOptions={{ color: '#e05b34', fillOpacity: 0.25 }} />
            ))}
          </MapContainer>
        </div>
      </div>
    </div>
  )
}

export default PredictionPage

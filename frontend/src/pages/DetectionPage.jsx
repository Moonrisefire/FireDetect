import { useEffect, useMemo, useRef, useState } from 'react'
import { detectImage } from '../services/api'
import { appendHistory } from '../services/cache'

function DetectionPage() {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [historyUpdated, setHistoryUpdated] = useState(false)
  const [fileInputKey, setFileInputKey] = useState(0)
  const imageRef = useRef(null)

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  const canAnalyze = !!file && !loading

  const previewStyle = useMemo(() => {
    if (!imageSize.width || !imageSize.height || !result?.detections) {
      return {}
    }
    return {
      minHeight: '320px',
      position: 'relative',
    }
  }, [imageSize, result])

  function handleFileChange(event) {
    setResult(null)
    setError('')
    setHistoryUpdated(false)
    const nextFile = event.target.files?.[0]
    if (nextFile) {
      setFile(nextFile)
      setPreviewUrl(URL.createObjectURL(nextFile))
    }
  }

  function handleImageLoad() {
    if (!imageRef.current) return
    setImageSize({ width: imageRef.current.naturalWidth, height: imageRef.current.naturalHeight })
  }

  function handleClearAll() {
    setResult(null)
    setFile(null)
    setPreviewUrl('')
    setImageSize({ width: 0, height: 0 })
    setError('')
    setHistoryUpdated(false)
    setFileInputKey(k => k + 1)
  }

  async function handleAnalyze() {
    if (!file) {
      setError('Please choose an image file first.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await detectImage(formData)
      const { is_fire, detections } = response
      const avgConfidence = detections && detections.length > 0 ? detections.reduce((sum, item) => sum + item.confidence, 0) / detections.length * 100 : 0
      const item = {
        id: `${Date.now()}-${file.name}`,
        timestamp: Date.now(),
        filename: file.name,
        is_fire: Boolean(is_fire),
        avgConfidence,
        detections: detections || [],
        previewUrl: previewUrl || '',
      }
      appendHistory(item)
      setResult({ is_fire: Boolean(is_fire), detections: detections || [] })
      setHistoryUpdated(true)
    } catch (err) {
      setError(err.message || 'Detection failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="detection-page">
      <div className="page-header">
        <div>
          <h1>Обнаружение</h1>
          <p>Выберите изображение пожара и проанализируйте его.</p>
        </div>
      </div>

      <div className="card card-form">
        <label className="file-field">
          <span>Choose an image</span>
          <input key={fileInputKey} type="file" accept="image/png,image/jpeg" onChange={handleFileChange} />
        </label>

        {file && (
          <div className="file-summary">
            <span>{file.name}</span>
            <span>{(file.size / 1024).toFixed(1)} KB</span>
          </div>
        )}

        <div className="form-actions">
          <button className="button button-primary" onClick={handleAnalyze} disabled={!canAnalyze}>
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
          <button className="button button-secondary" onClick={handleClearAll} type="button">
            Clear result
          </button>
        </div>

        {error && <div className="status-pill status-error">{error}</div>}
        {historyUpdated && !error && <div className="status-pill status-success">Результат сохранён</div>}
      </div>

      {previewUrl && (
        <section className="result-preview card">
          <h2>Preview</h2>
          <div className="image-preview" style={previewStyle}>
            <img
              ref={imageRef}
              src={previewUrl}
              alt="Selected preview"
              onLoad={handleImageLoad}
            />
            {imageSize.width > 0 && imageSize.height > 0 && result?.detections?.map((detection, index) => {
              const left = (detection.x_min / imageSize.width) * 100
              const top = (detection.y_min / imageSize.height) * 100
              const width = ((detection.x_max - detection.x_min) / imageSize.width) * 100
              const height = ((detection.y_max - detection.y_min) / imageSize.height) * 100
              return (
                <div
                  key={index}
                  className="detection-box"
                  style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
                >
                  <span className="detection-label">
                    {detection.label} {(detection.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {result && (
        <section className="detail-card card">
          <h2>Результат обнаружения</h2>
          <div className="result-status">
            <span className={result.is_fire ? 'status-badge fire' : 'status-badge safe'}>
              {result.is_fire ? 'Fire detected' : 'No fire detected'}
            </span>
            <span>{result.detections.length} detection(s)</span>
          </div>
        </section>
      )}
    </div>
  )
}

export default DetectionPage

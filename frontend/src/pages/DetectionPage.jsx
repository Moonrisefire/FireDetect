import { useEffect, useMemo, useRef, useState } from 'react'
import { detectImage, detectVideo } from '../services/api' // Оба импорта на месте
import { appendHistory } from '../services/cache'

function DetectionPage() {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [isVideo, setIsVideo] = useState(false) // Состояние для типа файла
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [historyUpdated, setHistoryUpdated] = useState(false)
  const [processedVideoUrl, setProcessedVideoUrl] = useState('') // Состояние для готового видео
  const imageRef = useRef(null)

  // Очистка ссылок при размонтировании страницы
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
      if (processedVideoUrl) URL.revokeObjectURL(processedVideoUrl)
    }
  }, [previewUrl, processedVideoUrl])

  const canAnalyze = !!file && !loading

  const previewStyle = useMemo(() => {
    if (!imageSize.width || !imageSize.height) {
      return {}
    }
    return {
      minHeight: '320px',
      position: 'relative',
    }
  }, [imageSize])

  // Перехватчик загрузки файла
  function handleFileChange(event) {
    setResult(null)
    setError('')
    setHistoryUpdated(false)
    setProcessedVideoUrl('') // Сброс старого результата видео
    setImageSize({ width: 0, height: 0 })

    const nextFile = event.target.files?.[0]
    if (nextFile) {
      setFile(nextFile)
      setPreviewUrl(URL.createObjectURL(nextFile))
      setIsVideo(nextFile.type.startsWith('video/')) // Автоопределение видео
    }
  }

  // Расчет размеров для картинок
  function handleImageLoad() {
    if (!imageRef.current) return
    setImageSize({
      width: imageRef.current.naturalWidth,
      height: imageRef.current.naturalHeight
    })
  }

  // Расчет размеров для видео
  function handleVideoLoad(event) {
    const videoElement = event.target
    setImageSize({
      width: videoElement.videoWidth,
      height: videoElement.videoHeight
    })
  }

  // Главная функция анализа
  async function handleAnalyze() {
    if (!file) {
      setError('Please choose a file first.')
      return
    }

    setLoading(true)
    setError('')
    setProcessedVideoUrl('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      if (isVideo) {
        // --- ОБРАБОТКА ВИДЕО ---
        const resultUrl = await detectVideo(formData)
        setProcessedVideoUrl(resultUrl)

        // Добавляем запись в историю для видео
        const item = {
          id: `${Date.now()}-${file.name}`,
          timestamp: Date.now(),
          filename: file.name,
          is_fire: true, // По умолчанию считаем, что видео отправлено на анализ пожара
          avgConfidence: 100,
          detections: [],
          previewUrl: previewUrl || '',
        }
        appendHistory(item)
        setResult({ is_fire: true, detections: [] })

      } else {
        // --- ОБРАБОТКА ФОТО ---
        const response = await detectImage(formData)
        const { is_fire, detections } = response

        const avgConfidence = detections && detections.length > 0
          ? (detections.reduce((sum, item) => sum + item.confidence, 0) / detections.length) * 100
          : 0

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
      }

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
          <p>Выберите изображение или видео пожара для анализа.</p>
        </div>
      </div>

      <div className="card card-form">
        <label className="file-field">
          <span>Choose an image or video</span>
          {/* Разрешаем выбор картинок и видео в проводнике */}
          <input type="file" accept="image/*,video/*" onChange={handleFileChange} />
        </label>

        {file && (
          <div className="file-summary">
            <span>{file.name}</span>
            <span>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
          </div>
        )}

        <div className="form-actions">
          <button className="button button-primary" onClick={handleAnalyze} disabled={!canAnalyze}>
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
          <button className="button button-secondary" onClick={() => { setResult(null); setProcessedVideoUrl(''); }} type="button">
            Clear result
          </button>
        </div>

        {error && <div className="status-pill status-error">{error}</div>}
        {historyUpdated && !error && <div className="status-pill status-success">Result saved to history</div>}
      </div>

      {/* Блок ПРЕДПРОСМОТРА (исходный файл) */}
      {previewUrl && (
        <section className="result-preview card">
          <h2>Preview</h2>
          <div className="image-preview" style={previewStyle}>
            {isVideo ? (
              <video
                key={previewUrl} // Ключ для мгновенного обновления плеера
                src={previewUrl}
                controls
                style={{ width: '100%', maxHeight: '450px', display: 'block', borderRadius: '8px' }}
                onLoadedMetadata={handleVideoLoad}
              />
            ) : (
              <img
                ref={imageRef}
                src={previewUrl}
                alt="Selected preview"
                onLoad={handleImageLoad}
              />
            )}

            {/* Отрисовка рамок поверх ИСХОДНОЙ КАРТИНКИ (для видео массив пустой, рамки не рисуются) */}
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

      {/* Блок ОБРАБОТАННОГО ВИДЕО С СЕРВЕРА */}
      {processedVideoUrl && (
        <section className="detail-card card">
          <h2>Результат анализа видео (со вшитыми рамками)</h2>
          <video
            src={processedVideoUrl}
            controls
            autoPlay
            style={{ width: '100%', borderRadius: '8px', marginTop: '15px' }}
          />
        </section>
      )}

      {result && !isVideo && (
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
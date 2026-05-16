import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchStats } from '../services/api'
import { loadHistory } from '../services/cache'
import ResultsHistory from '../components/ResultsHistory'
import shashlykImg from '../assets/ШАШЛЫКИ.png'

function HomePage() {
  const [stats, setStats] = useState({ imgs: 0, avg: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])

  useEffect(() => {
    setHistory(loadHistory())
  }, [])

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const data = await fetchStats()
        setStats({ imgs: data.imgs ?? 0, avg: data.avg ?? 0 })
      } catch (err) {
        setError('Unable to load stats from the backend.')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  return (
    <div className="home-page">
      <section className="hero-card card">
        <div className="hero-copy">
          <span className="eyebrow">Шашлыки</span>
          <img src={shashlykImg} alt="ШАШЛЫКИ" className="shashlyk" />
          <h1>Шашлыки</h1>
          <p>
            Загружайте изображения для обнаружения пожара, просматривайте недавние результаты 
            и исследуйте зоны риска возникновения пожара при помощи приложения ШАШЛЫКИ.
          </p>
          <div className="action-row">
            <Link to="/detection" className="button button-primary">
              Загрузить изображение
            </Link>
            <Link to="/prediction" className="button button-secondary">
              Посмотреть прогноз
            </Link>
          </div>
        </div>
        <div className="hero-stats card card-small">
          <h2>Статистика</h2>
          {loading ? (
            <div className="status-pill">Загрузка статистики…</div>
          ) : error ? (
            <div className="status-pill status-error">{error}</div>
          ) : (
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-label">Проанализированные изображения</span>
                <strong>{stats.imgs}</strong>
              </div>
              <div className="stat-card">
                <span className="stat-label">Средняя уверенность</span>
                <strong>{stats.avg.toFixed(2)}%</strong>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="about-card card">
        <h2>Как это работает</h2>
        <p>
          Фронтенд Шашлыков это небольшое одностраничное приложение, 
          которое использует API бэкенда для обнаружения и статистики. 
          Локальный кэш браузера хранит компактную историю недавних анализов, 
          чтобы вы могли быстро просмотреть результаты без зависимости от базы данных.
        </p>
        <ul>
          <li>Домашняя страница отображает статистику и историю обнаружения.</li>
          <li>Обнаружение позволяет загружать изображения и отображать рамки обнаружения пожара.</li>
          <li>Прогноз отображает зоны риска на карте и простую панель с оценкой.</li>
        </ul>
      </section>

      <ResultsHistory entries={history} />
    </div>
  )
}

export default HomePage

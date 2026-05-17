function ResultsHistory({ entries }) {
  return (
    <section className="history-panel">
      <div className="card card-compact">
        <div className="section-header">
          <div>
            <h2>История запросов</h2>
            <p>Тут хранится история ваших запросов.</p>
          </div>
        </div>

        {entries.length === 0 ? (
          <div className="empty-state">Нет результатов обнаружения. Запустите анализ, чтобы увидеть историю здесь.</div>
        ) : (
          <div className="history-list">
            {entries.map((entry) => (
              <article key={entry.id} className="history-entry">
                <div className="history-meta">
                  <strong>{entry.filename}</strong>
                  <span>{new Date(entry.timestamp).toLocaleString()}</span>
                </div>
                <div className="history-summary">
                  <span className={`status-badge ${entry.is_fire ? 'fire' : 'safe'}`}>
                    {entry.is_fire ? 'Fire' : 'No Fire'}
                  </span>
                  <span>{entry.detections.length} обнаружений</span>
                  <span>Средняя уверенность {entry.avgConfidence.toFixed(2)}%</span>
                </div>
                <div className="history-detail">
                  {entry.detections.map((item, index) => (
                    <div key={index} className="history-detail-item">
                      <span>{item.label}</span>
                      <span>{(item.confidence * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

export default ResultsHistory

const BASE_URL = 'http://localhost:8000'

async function handleResponse(response) {
  if (!response.ok) {
    const errorText = await response.text().catch(() => '')
    throw new Error(errorText || 'API request failed')
  }

  return response.json()
}

export async function fetchStats() {
  const response = await fetch(`${BASE_URL}/api/system/stats`)
  return handleResponse(response)
}

export async function detectImage(formData) {
  const response = await fetch(`${BASE_URL}/api/cv/detect_manual`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return response.json();
}

export async function fetchPrediction() {
  const response = await fetch(`${BASE_URL}/api/risk/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lat: 51.5335, lon: 45.9341 }),
  })
  if (!response.ok) throw new Error('Prediction endpoint not available')
  return handleResponse(response)
}

export async function startAnalysis(lat, lon) {
  const response = await fetch(`${BASE_URL}/api/risk/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lat, lon }),
  })
  if (!response.ok) throw new Error('Failed to start analysis')
  return handleResponse(response)
}

export async function pollJob(jobId) {
  const response = await fetch(`${BASE_URL}/api/risk/jobs/${jobId}`)
  if (!response.ok) throw new Error('Failed to poll job status')
  return handleResponse(response)
}

// Добавь эту функцию в api.js
export async function detectVideo(formData) {
  const response = await fetch(`${BASE_URL}/api/cv/detect_video`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Video detection failed');
  }

  const blob = await response.blob();
  const maxConfidence = Number(response.headers.get('x-max-confidence') || 0);
  return {
    url: URL.createObjectURL(blob),
    isFire: (response.headers.get('x-is-fire') || 'false').toLowerCase() === 'true',
    maxConfidence: Number.isFinite(maxConfidence) ? maxConfidence : 0,
  };
}
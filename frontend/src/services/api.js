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
  const response = await fetch('http://localhost:8080/api/detect_manual', {
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
    body: JSON.stringify({
      lat: 37.7749,
      lon: -122.4194,
    }),
  })
  if (!response.ok) {
    throw new Error('Prediction endpoint not available')
  }
  return handleResponse(response)
}

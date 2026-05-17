const STORAGE_KEY = 'fireDetectHistory'
const MAX_ENTRIES = 20

export function loadHistory() {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch (error) {
    return []
  }
}

export function saveHistory(entries) {
  if (typeof window === 'undefined') {
    return
  }

  const trimmed = entries.slice(0, MAX_ENTRIES)
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed))
}

export function appendHistory(entry) {
  const history = loadHistory()
  history.unshift(entry)
  saveHistory(history)
  return history
}

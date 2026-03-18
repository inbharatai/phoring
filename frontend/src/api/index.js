import axios from 'axios'

// ── Axios instance ─────────────────────────────────────────────────────────
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 300000, // 5-min for long LLM operations
  headers: { 'Content-Type': 'application/json' }
})

// ── Request interceptor ────────────────────────────────────────────────────
service.interceptors.request.use(
  config => config,
  error => {
    console.error('[API] Request error:', error)
    return Promise.reject(error)
  }
)

// ── User-friendly error messages ───────────────────────────────────────────
function humanizeError(error) {
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout'))
    return 'Request timed out — the server is taking too long. Please try again.'
  if (error.message === 'Network Error' || !navigator.onLine)
    return 'Cannot reach the server. Check that the backend is running on port 5001.'
  if (error.response) {
    const status = error.response.status
    const serverMsg = error.response.data?.error || error.response.data?.message
    if (serverMsg) return serverMsg
    if (status === 400) return 'Invalid request — check your inputs and try again.'
    if (status === 404) return 'Resource not found.'
    if (status === 500) return 'Server error — check backend logs for details.'
    return `Server returned ${status}.`
  }
  return error.message || 'An unexpected error occurred.'
}

// ── Response interceptor ───────────────────────────────────────────────────
service.interceptors.response.use(
  response => {
    const res = response.data
    if (res.success === false) {
      const msg = res.error || res.message || 'Unknown error'
      console.error('[API] Business error:', msg)
      const err = new Error(msg)
      err.isBusinessError = true
      err.data = res
      return Promise.reject(err)
    }
    return res
  },
  error => {
    const msg = humanizeError(error)
    console.error('[API] HTTP error:', msg, error)
    const enhanced = new Error(msg)
    enhanced.originalError = error
    enhanced.status = error.response?.status
    enhanced.data = error.response?.data

    // Emit global event so ErrorToast in App.vue can display it
    // Only emit for non-polling requests (status checks run frequently)
    const url = error.config?.url || ''
    const isPolling = url.includes('/status') || url.includes('/realtime') || url.includes('/agent-log') || url.includes('/console-log')
    if (!isPolling) {
      window.dispatchEvent(new CustomEvent('phoring:api-error', { detail: { message: msg } }))
    }

    return Promise.reject(enhanced)
  }
)

// ── Retry helper — exponential back-off ───────────────────────────────────
export const requestWithRetry = async (requestFn, maxRetries = 3, delay = 1000) => {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await requestFn()
    } catch (err) {
      // Don't retry on 4xx (client errors) — they won't fix themselves
      if (err.status >= 400 && err.status < 500) throw err
      if (attempt === maxRetries - 1) throw err
      const wait = delay * Math.pow(2, attempt)
      console.warn(`[API] Retry ${attempt + 1}/${maxRetries} in ${wait}ms...`)
      await new Promise(r => setTimeout(r, wait))
    }
  }
}

export default service


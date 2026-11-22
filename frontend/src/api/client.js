import { resolveSnapshotRequest, isSnapshotRequestAllowed } from './snapshot'
import { useUiStore } from '../store/ui'

const DEFAULT_API_URL = 'http://localhost:8000/api/v1'
const REQUEST_TIMEOUT_MS = 8000

export class ApiError extends Error {
  constructor({ code, message, details = {}, status = 0, requestId = null }) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.details = details
    this.status = status
    this.requestId = requestId
  }
}

export const API_URL = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/$/, '')

export async function apiRequest(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  if (useUiStore.getState().snapshotMode) {
    if (!isSnapshotRequestAllowed(path, method)) {
      throw new ApiError({
        code: 'SNAPSHOT_READ_ONLY',
        message: 'This saved replay is read-only. Reconnect to the backend to make changes.',
        status: 0,
      })
    }
    const payload = resolveSnapshotRequest(path, method)
    if (payload === null) {
      throw new ApiError({
        code: 'SNAPSHOT_DATA_MISSING',
        message: `The saved replay does not include ${path}.`,
        status: 0,
      })
    }
    return payload
  }

  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}${path.startsWith('/') ? path : `/${path}`}`, {
      ...options,
      headers: {
        ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...options.headers,
      },
      signal: options.signal || controller.signal,
    })

    const contentType = response.headers.get('content-type') || ''
    const payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text()

    if (!response.ok) {
      const error = payload?.error || {}
      throw new ApiError({
        code: error.code || `HTTP_${response.status}`,
        message: error.message || response.statusText || 'Request failed',
        details: error.details || {},
        status: response.status,
        requestId: response.headers.get('x-request-id'),
      })
    }
    return payload
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error.name === 'AbortError') {
      throw new ApiError({
        code: 'TIMEOUT',
        message: 'The server took too long to respond.',
        status: 0,
      })
    }
    throw new ApiError({
      code: 'BACKEND_UNREACHABLE',
      message: 'Cannot reach the RELAY backend.',
      status: 0,
    })
  } finally {
    window.clearTimeout(timeout)
  }
}

export const getHealth = () => apiRequest('/health')

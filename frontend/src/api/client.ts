import type {
  CrashClusterDetail,
  LocationSuggestionsResponse,
  RadarClustersResponse,
  RadarStatusResponse,
  TripCheckRequest,
  TripCheckResponse,
} from '../types/api'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const DEFAULT_API_TIMEOUT_MS = 15_000
const TRIP_CHECK_TIMEOUT_MS = 45_000

interface ApiFetchOptions extends RequestInit {
  timeoutMs?: number
  timeoutMessage?: string
}

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const {
    timeoutMs = DEFAULT_API_TIMEOUT_MS,
    timeoutMessage = 'RoadBuddy took too long to respond. Please try again.',
    signal: externalSignal,
    ...requestOptions
  } = options
  const controller = new AbortController()
  let timedOut = false

  const handleExternalAbort = () => controller.abort()
  if (externalSignal?.aborted) {
    controller.abort()
  } else {
    externalSignal?.addEventListener('abort', handleExternalAbort, { once: true })
  }

  const timeoutId = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...requestOptions.headers,
      },
    })

    if (!response.ok) {
      const body = await response.json().catch(() => null) as { detail?: string } | null
      throw new ApiError(
        body?.detail || 'RoadBuddy could not complete that request. Please try again.',
        response.status,
      )
    }

    return await response.json() as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError(
        timedOut
          ? timeoutMessage
          : 'RoadBuddy could not complete that request. Please try again.',
      )
    }
    throw new ApiError('RoadBuddy could not reach the service. Please try again.')
  } finally {
    window.clearTimeout(timeoutId)
    externalSignal?.removeEventListener('abort', handleExternalAbort)
  }
}

export function checkTrip(request: TripCheckRequest): Promise<TripCheckResponse> {
  return apiFetch('/trip/check', {
    method: 'POST',
    body: JSON.stringify(request),
    timeoutMs: TRIP_CHECK_TIMEOUT_MS,
    timeoutMessage: 'The trip check took too long. Please try again.',
  })
}

export function searchLocations(query: string): Promise<LocationSuggestionsResponse> {
  return apiFetch(`/trip/locations?q=${encodeURIComponent(query)}`)
}

export function getRadarClusters(
  bbox: string,
  zoom: number,
): Promise<RadarClustersResponse> {
  return apiFetch(
    `/radar/clusters?bbox=${encodeURIComponent(bbox)}&zoom=${encodeURIComponent(zoom.toFixed(2))}`,
  )
}

export function getRadarCluster(clusterId: number): Promise<CrashClusterDetail> {
  return apiFetch(`/radar/clusters/${clusterId}`)
}

export function getRadarStatus(): Promise<RadarStatusResponse> {
  return apiFetch('/radar/status')
}

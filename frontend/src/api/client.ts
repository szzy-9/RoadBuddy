import type {
  CrashClusterDetail,
  LocationSuggestionsResponse,
  RadarClustersResponse,
  RadarStatusResponse,
  TripCheckRequest,
  TripCheckResponse,
} from '../types/api'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })
  } catch {
    throw new ApiError('RoadBuddy could not reach the service. Please try again.')
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null
    throw new ApiError(
      body?.detail || 'RoadBuddy could not complete that request. Please try again.',
      response.status,
    )
  }

  return response.json() as Promise<T>
}

export function checkTrip(request: TripCheckRequest): Promise<TripCheckResponse> {
  return apiFetch('/trip/check', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export function searchLocations(query: string): Promise<LocationSuggestionsResponse> {
  return apiFetch(`/trip/locations?q=${encodeURIComponent(query)}`)
}

export function getRadarClusters(bbox: string): Promise<RadarClustersResponse> {
  return apiFetch(`/radar/clusters?bbox=${encodeURIComponent(bbox)}`)
}

export function getRadarCluster(clusterId: number): Promise<CrashClusterDetail> {
  return apiFetch(`/radar/clusters/${clusterId}`)
}

export function getRadarStatus(): Promise<RadarStatusResponse> {
  return apiFetch('/radar/status')
}

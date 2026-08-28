export type ConcernLevel = 'low' | 'medium' | 'higher'
export type DataAvailability = 'available' | 'unavailable'

export interface RouteSummary {
  origin: string
  destination: string
  distance_km: number
  duration_minutes: number
}

export interface RiskFactor {
  type: 'rain' | 'after_dark' | 'high_speed_zone' | 'significant_crash_history'
  label: string
}

export interface TripHotspot {
  cluster_id: number
  name: string | null
  crash_count: number
  dominant_type: string | null
  wet_count: number
  dark_count: number
  longitude: number
  latitude: number
}

export interface AlternativeDeparture {
  departure_time: string
  concern_level: ConcernLevel
  factor_count: number
}

export interface DepartureComparisonOption {
  departure_time: string
  arrival_time: string
  concern_level: ConcernLevel
  factor_count: number
}

export interface DepartureComparison {
  selected: DepartureComparisonOption
  thirty_minutes_later: DepartureComparisonOption
  difference_summary: string | null
}

export interface TripCheckResponse {
  route: RouteSummary
  concern_level: ConcernLevel
  factors: RiskFactor[]
  hotspots: TripHotspot[]
  alternative_departure: AlternativeDeparture | null
  departure_comparison: DepartureComparison
  data_status: {
    weather: DataAvailability
    crash_data: DataAvailability
    speed_zones: DataAvailability
  }
  rule_version: string
}

export interface TripCheckRequest {
  origin: string
  destination: string
  departure_time: string
}

export interface LocationSuggestion {
  label: string
  longitude: number
  latitude: number
}

export interface LocationSuggestionsResponse {
  suggestions: LocationSuggestion[]
}

export interface CrashClusterSummary {
  id: number
  name: string | null
  crash_count: number
  dominant_type: string | null
  longitude: number
  latitude: number
}

export interface CrashClusterDetail extends CrashClusterSummary {
  wet_count: number
  dark_count: number
  first_year: number | null
  last_year: number | null
}

export interface RadarClustersResponse {
  clusters: CrashClusterSummary[]
  data_status: DataAvailability
  last_updated: string | null
}

export interface RadarStatusResponse {
  crash_data: DataAvailability
  last_updated: string | null
  source: string | null
  licence: string | null
}

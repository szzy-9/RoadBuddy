export type ConcernLevel = 'low' | 'medium' | 'higher'
export type DataAvailability = 'available' | 'unavailable'

export interface GeoPoint {
  longitude: number
  latitude: number
}

export interface RouteSummary {
  origin: string
  destination: string
  /** Optional: absent on backends predating the coordinate fields. */
  origin_point?: GeoPoint
  destination_point?: GeoPoint
  distance_km: number
  duration_minutes: number
}

export interface RiskFactor {
  type: 'rain' | 'after_dark' | 'high_speed_zone' | 'significant_crash_history'
  label: string
}

export interface TripHotspot {
  cluster_id: number
  crash_count: number
  eligible_driver_age_crashes: number
  young_driver_crashes: number
  young_driver_pct: number | null
  young_driver_pct_displayable: boolean
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
  /** Optional: absent on backends predating the per-option reason. */
  factors?: RiskFactor[]
  reason?: string | null
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
  crash_count: number
  eligible_driver_age_crashes: number
  young_driver_crashes: number
  young_driver_pct: number | null
  young_driver_pct_displayable: boolean
  longitude: number
  latitude: number
}

export interface CrashClusterDetail extends CrashClusterSummary {
  first_year: number | null
  last_year: number | null
  /** Optional: absent on backends predating the cluster context fields. */
  road_name?: string | null
  dominant_crash_type?: string | null
  wet_crashes?: number | null
  dark_crashes?: number | null
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

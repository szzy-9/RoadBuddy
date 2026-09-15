export type ConcernLevel = 'low' | 'medium' | 'higher'
export type DataAvailability = 'available' | 'unavailable'

export interface IndicatorExplanation {
  source: string
  trigger: string
  limitation?: string
}

export interface GeoPoint {
  longitude: number
  latitude: number
}

export interface GeoLineString {
  type: 'LineString'
  coordinates: [number, number][]
}

export interface RouteRiskSegment {
  index: number
  geometry: GeoLineString
  /** null means crash data is unavailable, not zero recorded crashes. */
  nearby_crash_count: number | null
}

export interface RouteSummary {
  origin: string
  destination: string
  /** Optional: absent on backends predating the coordinate fields. */
  origin_point?: GeoPoint
  destination_point?: GeoPoint
  distance_km: number
  duration_minutes: number
  geometry: GeoLineString
  segments: RouteRiskSegment[]
}

export interface RiskFactor {
  type: 'rain' | 'after_dark' | 'high_speed_zone' | 'significant_crash_history'
  label: string
  explanation?: IndicatorExplanation | null
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
  /**
   * The coordinates behind a picked suggestion.
   *
   * Sent so the server routes from the exact place the user chose. Omitted for
   * an address typed without picking, which the server still geocodes.
   */
  origin_point?: GeoPoint
  destination_point?: GeoPoint
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
  explanation?: IndicatorExplanation | null
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

export interface LearnOption {
  key: string
  text: string
}

export interface LearnSource {
  id: string
  name: string
  section: string | null
  url: string | null
}

export interface LearnScenario {
  type: string
  description: string | null
  hazards: string[]
  decision_point: string | null
  media_reference: string | null
}

export interface LearnTopic {
  id: string
  name: string
  description: string | null
  trip_matchable: boolean
}

export interface LearnTopicsResponse {
  topics: LearnTopic[]
}

export interface MockTestQuestion {
  id: string
  topic_id: string
  difficulty: string
  question_type: string
  prompt: string
  options: LearnOption[]
  scenario: LearnScenario | null
}

export interface LearnQuestionPrompt extends MockTestQuestion {
  subtopic: string | null
  source: LearnSource
}

export interface LearnQuestion extends LearnQuestionPrompt {
  explanation: string
}

export interface LearnQuestionsResponse {
  questions: LearnQuestion[]
}

export interface MockTestResponse {
  total_questions: number
  pass_mark_percent: number
  questions: MockTestQuestion[]
}

export interface MockTestAnswer {
  question_id: string
  selected_option: string
}

export interface MockTestGradeRequest {
  answers: MockTestAnswer[]
}

export type MockTestQuestionResult = LearnAnswerResponse

export interface MockTestGradeResponse {
  score: number
  total: number
  percentage: number
  pass_mark_percent: number
  passed: boolean
  results: MockTestQuestionResult[]
}

export interface TripLessonRequest {
  risk_factors: RiskFactor['type'][]
}

export interface TripLessonResponse {
  available: boolean
  matched_risk_factors: RiskFactor['type'][]
  matched_topics: string[]
  questions: LearnQuestionPrompt[]
}

export interface LearnAnswerRequest {
  selected_option: string
}

export interface LearnAnswerResponse {
  question_id: string
  selected_option: string
  correct_option: string
  correct: boolean
  explanation: string
  source: LearnSource
}

export interface AskRequest {
  question: string
}

export interface AskSource {
  name: string
  excerpt: string
}

export interface AskResponse {
  answered: boolean
  answer: string
  sources: AskSource[]
  /**
   * Why a question was declined: not_in_sources, off_topic, unavailable.
   * Also "greeting" for a conversational turn, which is not a decline.
   */
  reason: string | null
  /** Questions to offer the user, sent with a greeting. */
  examples: string[]
}

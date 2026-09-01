import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import ConcernBadge from '../components/ConcernBadge'
import RiskFactorCard from '../components/RiskFactorCard'
import { useTripResult } from '../state/tripResult'
import type { DepartureComparisonOption, RiskFactor, TripCheckResponse } from '../types/api'

type DetailMode = 'comparison' | 'conditions' | 'hotspots' | null

/**
 * Format a departure timestamp for prose, e.g. "Mon 6:30 pm".
 *
 * @param value - An ISO 8601 timestamp.
 * @returns A short weekday-and-time string in Australian English.
 */
function formatDeparture(value: string): string {
  return new Intl.DateTimeFormat('en-AU', {
    weekday: 'short',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

/**
 * Format a timestamp as 24-hour clock time for the comparison cards.
 *
 * @param value - An ISO 8601 timestamp.
 * @returns A zero-padded "HH:mm" string.
 */
function formatComparisonTime(value: string): string {
  return new Intl.DateTimeFormat('en-AU', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

/**
 * Build the notice shown when one or more upstream data sources were missing.
 *
 * Wording stays explicit that nothing has been inferred from absent data.
 *
 * @param dataStatus - Per-source availability from the trip check.
 * @returns A sentence naming the unavailable sources, or null when all present.
 */
function partialDataMessage(dataStatus: TripCheckResponse['data_status']): string | null {
  const weatherUnavailable = dataStatus.weather === 'unavailable'
  const crashUnavailable = dataStatus.crash_data === 'unavailable'
  const speedZonesUnavailable = dataStatus.speed_zones === 'unavailable'
  const unavailableCount = [
    weatherUnavailable,
    crashUnavailable,
    speedZonesUnavailable,
  ].filter(Boolean).length

  if (unavailableCount === 0) return null
  if (unavailableCount === 1) {
    if (weatherUnavailable) {
      return 'Weather data is unavailable. This check uses the other available information.'
    }
    if (crashUnavailable) {
      return 'Crash history is unavailable. No crash information has been inferred.'
    }
    return 'Speed-zone data is unavailable. This check does not include speed-zone context.'
  }

  const unavailableSources = [
    weatherUnavailable ? 'weather data' : null,
    crashUnavailable ? 'crash history' : null,
    speedZonesUnavailable ? 'speed-zone data' : null,
  ].filter((source): source is string => source !== null)
  const sourceSummary = unavailableSources.length === 2
    ? unavailableSources.join(' and ')
    : `${unavailableSources.slice(0, -1).join(', ')} and ${unavailableSources.at(-1)}`
  const capitalizedSourceSummary = sourceSummary[0].toUpperCase() + sourceSummary.slice(1)
  const limitations = [
    crashUnavailable ? 'no crash information has been inferred' : null,
    speedZonesUnavailable ? 'speed-zone context is not included' : null,
  ].filter((limitation): limitation is string => limitation !== null)
  const limitationSummary = limitations.length > 0
    ? `; ${limitations.join(' and ')}`
    : ''

  return `${capitalizedSourceSummary} are unavailable. This check uses the remaining available information${limitationSummary}.`
}

/** Terse forms of each factor, for the line under a concern badge. */
const SHORT_FACTOR_LABELS: Record<RiskFactor['type'], string> = {
  rain: 'rain',
  after_dark: 'after dark',
  high_speed_zone: 'high-speed road',
  significant_crash_history: 'crash history',
}

/**
 * Describe why a departure option carries its concern level.
 *
 * Prefers the backend's own phrasing, then the option's own factors. A backend
 * predating both still explains the selected option, whose conditions are the
 * trip's top-level factors; the later option has no such fallback, since its
 * conditions genuinely differ and must not be guessed at.
 *
 * @param option - The departure option to explain.
 * @param fallbackFactors - Factors to use when the option carries none.
 * @returns A short phrase, or null when nothing is known.
 */
function departureReason(
  option: DepartureComparisonOption,
  fallbackFactors?: RiskFactor[],
): string | null {
  if (option.reason) return option.reason
  const factors = option.factors?.length ? option.factors : fallbackFactors
  if (!factors?.length) return null
  return factors.map((factor) => SHORT_FACTOR_LABELS[factor.type]).join(', ')
}

/**
 * One departure option card, showing its concern level and why.
 *
 * @param props.label - Heading for the option ("Now" / "30 min later").
 * @param props.option - The departure option to render.
 * @returns The option card.
 */
function DepartureOptionCard({
  label,
  option,
  fallbackFactors,
}: {
  label: string
  option: DepartureComparisonOption
  fallbackFactors?: RiskFactor[]
}) {
  const reason = departureReason(option, fallbackFactors)

  return (
    <article className="departure-comparison-option">
      <p>{label}</p>
      <dl>
        <div>
          <dt>Departure</dt>
          <dd>{formatComparisonTime(option.departure_time)}</dd>
        </div>
        <div>
          <dt>Arrival</dt>
          <dd>{formatComparisonTime(option.arrival_time)}</dd>
        </div>
      </dl>
      <ConcernBadge level={option.concern_level} />
      {/* Say why the badge reads as it does, so the level is never unexplained. */}
      {reason ? (
        <p className="departure-option-reason">Due to {reason}</p>
      ) : option.concern_level === 'low' ? (
        <p className="departure-option-reason">No concern conditions identified</p>
      ) : null}
    </article>
  )
}

/**
 * Result screen for a completed trip check.
 *
 * A single /trip/check response carries everything the detail panels show, so
 * they render from the stored result rather than refetching. Reading from the
 * store rather than router state means the result survives a visit to the Risk
 * Radar and a page refresh.
 *
 * @returns The result screen, or a redirect when no result is stored.
 */
export default function TripResultPage() {
  const [result, clearResult] = useTripResult()
  const [detailMode, setDetailMode] = useState<DetailMode>(null)

  useEffect(() => {
    if (!detailMode) return

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDetailMode(null)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [detailMode])

  if (!result) return <Navigate to="/trip" replace />

  const hotspotSummary = result.data_status.crash_data === 'unavailable'
    ? 'Crash history unavailable'
    : result.hotspots.length === 0
      ? 'No major hotspots found'
      : `${result.hotspots.length} major ${result.hotspots.length === 1 ? 'hotspot' : 'hotspots'}`
  const conditionsSummary = `${result.factors.length} contributing`
  const comparisonSummary =
    `${formatComparisonTime(result.departure_comparison.selected.departure_time)} now`
    + ' → '
    + `${formatComparisonTime(result.departure_comparison.thirty_minutes_later.departure_time)} later`

  const dataMessage = partialDataMessage(result.data_status)

  // The destination label always exists, so the Radar search box is prefilled
  // even on backends that omit route coordinates; those simply cannot fly the
  // map to the destination, and open on the default view instead.
  const destinationPoint = result.route.destination_point
  const radarFocusState = {
    focus: {
      label: result.route.destination,
      longitude: destinationPoint?.longitude,
      latitude: destinationPoint?.latitude,
    },
  }

  return (
    <div className="trip-result-page">
      <header className="screen-header">
        <div>
          <p className="eyebrow">Trip check</p>
          <h1>Road conditions</h1>
        </div>
        <Link className="screen-header-link" to="/trip">Change trip</Link>
      </header>

      <section className="result-overview" aria-live="polite">
        <div className="result-route">
          <strong>{result.route.origin}</strong>
          <span aria-hidden="true">→</span>
          <strong>{result.route.destination}</strong>
        </div>
        <div className="result-level-row">
          <ConcernBadge level={result.concern_level} />
          <div className="route-stats">
            <span><strong>{result.route.distance_km.toFixed(1)}</strong> km</span>
            <span><strong>{result.route.duration_minutes}</strong> min</span>
          </div>
        </div>
        <p>This is a condition check, not a prediction that a crash will occur.</p>
      </section>

      <div className="result-detail-actions">
        <button type="button" onClick={() => setDetailMode('comparison')}>
          <span className="result-detail-icon" aria-hidden="true">◷</span>
          <span>
            <strong>Departure comparison</strong>
            <small>{comparisonSummary}</small>
          </span>
          <span aria-hidden="true">→</span>
        </button>
        <button type="button" onClick={() => setDetailMode('conditions')}>
          <span className="result-detail-icon" aria-hidden="true">☂</span>
          <span><strong>Conditions</strong><small>{conditionsSummary}</small></span>
          <span aria-hidden="true">→</span>
        </button>
        <button type="button" onClick={() => setDetailMode('hotspots')}>
          <span className="result-detail-icon" aria-hidden="true">◎</span>
          <span><strong>Crash hotspots</strong><small>{hotspotSummary}</small></span>
          <span aria-hidden="true">→</span>
        </button>
      </div>

      <div className="result-context">
        {result.alternative_departure && (
          <aside className="result-context-note alternative">
            <strong>Lower-concern option</strong>
            <span>Leave {formatDeparture(result.alternative_departure.departure_time)}</span>
          </aside>
        )}
        {dataMessage && (
          <aside className="result-context-note warning">
            {dataMessage}
          </aside>
        )}
      </div>

      <div className="result-actions">
        <Link className="button button-secondary" to="/radar" state={radarFocusState}>
          View Risk Radar
        </Link>
        <Link className="text-button" to="/trip" onClick={clearResult}>
          Check another trip
        </Link>
      </div>

      {detailMode && (
        <div className="sheet-backdrop" onMouseDown={() => setDetailMode(null)}>
          <section
            className="trip-detail-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby="trip-detail-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button
              className="sheet-close"
              type="button"
              onClick={() => setDetailMode(null)}
              aria-label="Close details"
            >
              ×
            </button>

            {detailMode === 'comparison' ? (
              <>
                <p className="eyebrow">Departure comparison</p>
                <h2 id="trip-detail-title">Compare your options</h2>
                <div className="departure-comparison-grid">
                  <DepartureOptionCard
                    label="Now"
                    option={result.departure_comparison.selected}
                    fallbackFactors={result.factors}
                  />
                  <DepartureOptionCard
                    label="30 min later"
                    option={result.departure_comparison.thirty_minutes_later}
                  />
                </div>
                {result.departure_comparison.difference_summary && (
                  <p className="departure-difference">
                    {result.departure_comparison.difference_summary}
                  </p>
                )}
              </>
            ) : detailMode === 'conditions' ? (
              <>
                <p className="eyebrow">Contributing conditions</p>
                <h2 id="trip-detail-title">What shaped this result</h2>
                {result.factors.length > 0 ? (
                  <div className="factor-grid">
                    {result.factors.map((factor) => (
                      <RiskFactorCard key={factor.type} factor={factor} />
                    ))}
                  </div>
                ) : (
                  <p className="empty-note">No included concern conditions were identified.</p>
                )}
              </>
            ) : (
              <>
                <p className="eyebrow">Historical context</p>
                <h2 id="trip-detail-title">Major crash hotspots</h2>
                {result.data_status.crash_data === 'unavailable' ? (
                  <p className="empty-note">
                    Crash history is unavailable. No crash information has been inferred.
                  </p>
                ) : result.hotspots.length > 0 ? (
                  <div className="hotspot-list">
                    {result.hotspots.map((hotspot) => (
                      <article key={hotspot.cluster_id} className="hotspot-row">
                        <span className="hotspot-count">{hotspot.crash_count}</span>
                        <div>
                          <h3>{hotspot.crash_count} historical injury crashes</h3>
                          <p>
                            {hotspot.young_driver_crashes} involved a driver aged 16–25
                            {hotspot.young_driver_pct_displayable && hotspot.young_driver_pct !== null
                              ? ` · ${hotspot.young_driver_pct.toFixed(2)}% of crashes with known-age drivers`
                              : ' · Insufficient historical data for a young-driver percentage'}
                          </p>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="empty-note">No major crash hotspots were found near this route.</p>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

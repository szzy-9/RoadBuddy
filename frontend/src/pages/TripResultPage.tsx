import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import ConcernBadge from '../components/ConcernBadge'
import RiskFactorCard from '../components/RiskFactorCard'
import type { DepartureComparison, TripCheckResponse } from '../types/api'

type DetailMode = 'comparison' | 'conditions' | 'hotspots' | null

interface TripResultLocationState {
  tripResult?: TripCheckResponse
}

function formatDeparture(value: string): string {
  return new Intl.DateTimeFormat('en-AU', {
    weekday: 'short',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatComparisonTime(value: string): string {
  return new Intl.DateTimeFormat('en-AU', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

function DepartureComparisonContent({ comparison }: { comparison: DepartureComparison }) {
  const options = [
    { label: 'Now', value: comparison.selected },
    { label: '30 min later', value: comparison.thirty_minutes_later },
  ]

  return (
    <>
      <p className="eyebrow">Departure comparison</p>
      <h2 id="trip-detail-title">Compare your options</h2>
      <div className="departure-comparison-grid">
        {options.map((option) => (
          <article className="departure-comparison-option" key={option.label}>
            <p>{option.label}</p>
            <dl>
              <div>
                <dt>Departure</dt>
                <dd>{formatComparisonTime(option.value.departure_time)}</dd>
              </div>
              <div>
                <dt>Arrival</dt>
                <dd>{formatComparisonTime(option.value.arrival_time)}</dd>
              </div>
            </dl>
            <ConcernBadge level={option.value.concern_level} />
          </article>
        ))}
      </div>
      {comparison.difference_summary && (
        <p className="departure-difference">{comparison.difference_summary}</p>
      )}
    </>
  )
}

export default function TripResultPage() {
  const location = useLocation()
  const result = (location.state as TripResultLocationState | null)?.tripResult
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
            <small>
              {formatComparisonTime(result.departure_comparison.selected.departure_time)} now
              {' → '}
              {formatComparisonTime(
                result.departure_comparison.thirty_minutes_later.departure_time,
              )} later
            </small>
          </span>
          <span aria-hidden="true">→</span>
        </button>
        <button type="button" onClick={() => setDetailMode('conditions')}>
          <span className="result-detail-icon" aria-hidden="true">☂</span>
          <span><strong>Conditions</strong><small>{result.factors.length} contributing</small></span>
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
        {result.data_status.weather === 'unavailable' && (
          <aside className="result-context-note warning">
            Weather unavailable — this result uses the other available information.
          </aside>
        )}
      </div>

      <div className="result-actions">
        <Link className="button button-secondary" to="/radar">View Risk Radar</Link>
        <Link className="text-button" to="/trip">Check another trip</Link>
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
              <DepartureComparisonContent comparison={result.departure_comparison} />
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
                  <p className="empty-note">Crash history is unavailable. No crash information has been inferred.</p>
                ) : result.hotspots.length > 0 ? (
                  <div className="hotspot-list">
                    {result.hotspots.map((hotspot) => (
                      <article key={hotspot.cluster_id} className="hotspot-row">
                        <span className="hotspot-count">{hotspot.crash_count}</span>
                        <div>
                          <h3>{hotspot.name || 'Unnamed location'}</h3>
                          <p>{hotspot.dominant_type || 'Crash type unavailable'}</p>
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

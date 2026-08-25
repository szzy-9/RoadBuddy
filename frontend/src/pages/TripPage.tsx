import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { checkTrip } from '../api/client'
import AddressAutocomplete from '../components/AddressAutocomplete'
import ConcernBadge from '../components/ConcernBadge'
import ErrorMessage from '../components/ErrorMessage'
import LoadingState from '../components/LoadingState'
import RiskFactorCard from '../components/RiskFactorCard'
import type { TripCheckResponse } from '../types/api'

function localDateTimeDefault(): string {
  const date = new Date(Date.now() + 30 * 60 * 1000)
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function withLocalOffset(localValue: string): string {
  const date = new Date(localValue)
  if (Number.isNaN(date.getTime())) return ''
  const offsetMinutes = -date.getTimezoneOffset()
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const absolute = Math.abs(offsetMinutes)
  const hours = String(Math.floor(absolute / 60)).padStart(2, '0')
  const minutes = String(absolute % 60).padStart(2, '0')
  return `${localValue}:00${sign}${hours}:${minutes}`
}

function formatDeparture(value: string): string {
  return new Intl.DateTimeFormat('en-AU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

export default function TripPage() {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [departureTime, setDepartureTime] = useState(localDateTimeDefault)
  const [result, setResult] = useState<TripCheckResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (!origin.trim()) {
      setError('Enter where you are leaving from.')
      return
    }
    if (!destination.trim()) {
      setError('Enter where you are going.')
      return
    }
    const formattedDeparture = withLocalOffset(departureTime)
    if (!formattedDeparture) {
      setError('Choose a valid departure date and time.')
      return
    }

    setIsLoading(true)
    setResult(null)
    try {
      const response = await checkTrip({
        origin: origin.trim(),
        destination: destination.trim(),
        departure_time: formattedDeparture,
      })
      setResult(response)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Something went wrong. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="trip-page page-wrap">
      <section className="page-heading">
        <p className="eyebrow">Pre-journey risk check</p>
        <h1>Check the road ahead.</h1>
        <p className="lead">See the conditions that may deserve more care before you leave.</p>
      </section>

      <form className="trip-form" onSubmit={handleSubmit} noValidate>
        <div className="journey-fields">
          <AddressAutocomplete
            label="From address"
            value={origin}
            onChange={setOrigin}
            placeholder="e.g. Tarneit VIC 3029"
          />
          <span className="journey-arrow" aria-hidden="true">→</span>
          <AddressAutocomplete
            label="To address"
            value={destination}
            onChange={setDestination}
            placeholder="e.g. Docklands VIC 3008"
          />
        </div>
        <label className="departure-field">
          <span>Departure date and time</span>
          <input
            type="datetime-local"
            value={departureTime}
            onChange={(event) => setDepartureTime(event.target.value)}
          />
        </label>
        <button className="button button-primary submit-button" type="submit" disabled={isLoading}>
          {isLoading ? 'Checking…' : 'Check this trip'}
        </button>
        <p className="form-privacy">Addresses are used for this check only and are not stored.</p>
      </form>

      {error && <ErrorMessage message={error} />}
      {isLoading && <LoadingState />}

      {result && (
        <section className="trip-result" aria-live="polite">
          <div className="result-hero">
            <div className="result-summary">
              <p className="card-kicker">Trip overview</p>
              <h2>{result.route.origin} <span aria-hidden="true">→</span> {result.route.destination}</h2>
              <ConcernBadge level={result.concern_level} />
            </div>
            <div className="route-stats">
              <div><strong>{result.route.distance_km.toFixed(1)}</strong><span>km</span></div>
              <div><strong>{result.route.duration_minutes}</strong><span>minutes</span></div>
            </div>
            <p className="result-caveat">
              This is a transparent condition check, not a prediction that a crash will occur.
            </p>
          </div>

          <div className="result-section">
            <div className="section-title-row">
              <div>
                <p className="eyebrow">Contributing conditions</p>
                <h2>What shaped this result</h2>
              </div>
              <span className="count-pill">{result.factors.length}</span>
            </div>
            {result.factors.length > 0 ? (
              <div className="factor-grid">
                {result.factors.map((factor) => <RiskFactorCard key={factor.type} factor={factor} />)}
              </div>
            ) : (
              <p className="empty-note">No included concern conditions were identified for this check.</p>
            )}
          </div>

          <div className="result-section">
            <div className="section-title-row">
              <div>
                <p className="eyebrow">Historical context</p>
                <h2>Major crash hotspots along the route</h2>
              </div>
            </div>
            {result.data_status.crash_data === 'unavailable' ? (
              <p className="empty-note">Crash history is unavailable for this check. No crash information has been inferred.</p>
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
          </div>

          {result.alternative_departure && (
            <aside className="alternative-card">
              <span aria-hidden="true">＋30</span>
              <div>
                <p className="eyebrow">A lower-concern option</p>
                <h2>Consider leaving at {formatDeparture(result.alternative_departure.departure_time)}</h2>
                <p>This time had fewer included concern conditions in the same prototype check.</p>
              </div>
            </aside>
          )}

          {result.data_status.weather === 'unavailable' && (
            <p className="data-warning">Weather was unavailable, so this result uses route and historical information only.</p>
          )}

          <div className="result-actions">
            <Link className="button button-secondary" to="/radar">View Risk Radar</Link>
            <button className="text-button" type="button" onClick={() => setResult(null)}>Check another trip</button>
          </div>
        </section>
      )}
    </div>
  )
}

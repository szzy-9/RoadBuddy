import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getRadarStatus } from '../api/client'

export default function HomePage() {
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  useEffect(() => {
    getRadarStatus()
      .then((status) => setLastUpdated(status.last_updated))
      .catch(() => undefined)
  }, [])

  return (
    <section className="home-page">
      <div className="hero-copy">
        <p className="eyebrow">Plan with context. Drive with care.</p>
        <h1>Understand your next drive before you take it.</h1>
        <p className="lead">
          Check the conditions that can make a familiar drive more demanding,
          from weather and darkness to historical crash patterns.
        </p>
        <div className="hero-actions">
          <Link className="button button-primary" to="/trip">Check a trip</Link>
          <Link className="button button-secondary" to="/radar">Open Risk Radar</Link>
        </div>
        <p className="privacy-note">
          <span aria-hidden="true">●</span>
          No account required. Trip addresses are not stored.
        </p>
      </div>

      <aside className="hero-card" aria-label="Road condition preview">
        <div className="route-line" aria-hidden="true">
          <span className="route-dot route-dot-start" />
          <span className="route-path" />
          <span className="route-dot route-dot-end" />
        </div>
        <div>
          <p className="card-kicker">Your drive, in context</p>
          <h2>See what deserves more attention.</h2>
        </div>
        <div className="context-grid">
          <div><span className="weather-symbol" aria-hidden="true">☂</span><small>Weather</small></div>
          <div><span className="weather-symbol" aria-hidden="true">◒</span><small>Daylight</small></div>
          <div><span className="weather-symbol" aria-hidden="true">⌖</span><small>Crash history</small></div>
        </div>
        <p className="dataset-date">
          {lastUpdated
            ? `Crash dataset refreshed ${new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(lastUpdated))}.`
            : 'Crash data refresh date will appear when available.'}
        </p>
      </aside>
    </section>
  )
}

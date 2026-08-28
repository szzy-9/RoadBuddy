import { useState } from 'react'
import { Link } from 'react-router-dom'

type HomeState = 'first-open' | 'returning'

export const HOME_DEMO_STATE_KEY = 'roadbuddy.homeState'

function getInitialHomeState(): HomeState {
  try {
    return window.localStorage.getItem(HOME_DEMO_STATE_KEY) === 'returning'
      ? 'returning'
      : 'first-open'
  } catch {
    return 'first-open'
  }
}

function HomeListCard({
  icon,
  title,
  description,
  to,
}: {
  icon: string
  title: string
  description: string
  to?: string
}) {
  const content = (
    <>
      <span className="home-list-icon" aria-hidden="true">{icon}</span>
      <span className="home-list-copy">
        <strong>{title}</strong>
        <small>{description}</small>
      </span>
      <span className="home-list-arrow" aria-hidden="true">→</span>
    </>
  )

  if (to) {
    return (
      <Link className="home-list-card" to={to} aria-label={`${title}: ${description}`}>
        {content}
      </Link>
    )
  }

  return <article className="home-list-card">{content}</article>
}

export default function HomePage() {
  const [homeState, setHomeState] = useState<HomeState>(getInitialHomeState)

  function showReturningState() {
    try {
      window.localStorage.setItem(HOME_DEMO_STATE_KEY, 'returning')
    } catch {
      // The visual demo still works when browser storage is unavailable.
    }
    setHomeState('returning')
  }

  return (
    <section className="home-page">
      {homeState === 'first-open' ? (
        <div className="home-state home-state-first">
          <article className="home-primary-card home-first-card">
            <span className="home-primary-icon" aria-hidden="true">📍</span>
            <h1>No trips saved yet</h1>
            <p>
              Save home and work once. After that a<br />
              trip check is two taps.
            </p>
            <button className="home-primary-cta" type="button" onClick={showReturningState}>
              + Add a place
            </button>
          </article>

          <p className="home-separator">OR START HERE</p>

          <HomeListCard
            icon="🌙"
            title="Night driving"
            description="One question, about two minutes"
          />

          <aside className="home-privacy-note">
            No account, no sign-up. Nothing you type<br />
            leaves this device.
          </aside>
        </div>
      ) : (
        <div className="home-state home-state-returning">
          <article className="home-primary-card home-returning-card">
            <h1>Tarneit <span aria-hidden="true">→</span> Docklands</h1>
            <p>
              Leaving at 22:40, and it should be<br />
              raining 🌧️
            </p>
            <Link className="home-primary-cta" to="/trip">
              Check this trip →
            </Link>
          </article>

          <div className="home-card-stack">
            <HomeListCard
              icon="🌧️"
              title="Tonight's lesson"
              description="Driving a wet freeway after dark"
            />
            <HomeListCard
              icon="🗺️"
              title="Risk Radar"
              description="2 disruptions near your route"
              to="/radar"
            />
          </div>

          <p className="home-refresh-text">Crash data refreshed 12 Aug 2026</p>
        </div>
      )}
    </section>
  )
}

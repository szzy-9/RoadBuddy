import { useState } from 'react'
import { Link } from 'react-router-dom'

type HomeState = 'first-open' | 'returning'

export const HOME_DEMO_STATE_KEY = 'roadbuddy.homeState'

/**
 * The home screen currently opens straight on the returning state.
 *
 * Temporary: the first-open state offers "+ Add a place", which only flips this
 * flag and saves nothing, so it promises a feature that does not exist yet.
 * Restore the stored-state version below once saving a place is real.
 */
function getInitialHomeState(): HomeState {
  return 'returning'
}

// function getInitialHomeState(): HomeState {
//   try {
//     return window.localStorage.getItem(HOME_DEMO_STATE_KEY) === 'returning'
//       ? 'returning'
//       : 'first-open'
//   } catch {
//     return 'first-open'
//   }
// }

/**
 * What a trip check looks at, shown on the home card so the app explains
 * itself before asking for an address.
 *
 * Each entry names a real risk factor the backend returns, so the promise here
 * matches what the result screen actually shows.
 */
const CHECK_HIGHLIGHTS: Array<{ icon: string; label: string }> = [
  { icon: '\u{1F327}\uFE0F', label: 'Rain on the way' },
  { icon: '\u{1F319}', label: 'Driving after dark' },
  { icon: '\u{1F6A6}', label: 'High-speed roads' },
  { icon: '\u{1F4CD}', label: 'Past crash hotspots' },
]

function HomeListCard({
  icon,
  title,
  description,
  to,
}: {
  icon: string
  title: string
  description?: string
  to?: string
}) {
  const content = (
    <>
      <span className="home-list-icon" aria-hidden="true">{icon}</span>
      <span className="home-list-copy">
        <strong>{title}</strong>
        {description ? <small>{description}</small> : null}
      </span>
      <span className="home-list-arrow" aria-hidden="true">→</span>
    </>
  )

  if (to) {
    return (
      <Link
        className="home-list-card"
        to={to}
        aria-label={description ? `${title}: ${description}` : title}
      >
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
            <p className="home-eyebrow">BEFORE YOU DRIVE</p>
            <h1>Know what the road throws at you</h1>
            <p className="home-primary-blurb">
              Tell us where you are heading and when. We check the conditions on
              that route and flag what deserves extra care.
            </p>
            <ul className="home-highlights">
              {CHECK_HIGHLIGHTS.map((highlight) => (
                <li key={highlight.label}>
                  <span aria-hidden="true">{highlight.icon}</span>
                  {highlight.label}
                </li>
              ))}
            </ul>
            <Link className="home-primary-cta" to="/trip">
              Check my trip →
            </Link>
          </article>

          <div className="home-card-stack">
            {/* Tonight's lesson card hidden for now.
            <HomeListCard
              icon="🌧️"
              title="Tonight's lesson"
              description="Driving a wet freeway after dark"
            />
            */}
            <HomeListCard
              icon="🗺️"
              title="Risk Radar"
              description="Map of past crash hotspots around you"
              to="/radar"
            />
          </div>

          <p className="home-refresh-text">Crash data refreshed 12 Aug 2026</p>
        </div>
      )}
    </section>
  )
}

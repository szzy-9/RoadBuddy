import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { checkTrip } from '../api/client'
import { saveTripResult } from '../state/tripResult'

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
 * Sample Victorian trips offered on the home card.
 *
 * Each entry is a real suburb-and-postcode pair the geocoder resolves, so the
 * demo trip runs through the same check as a hand-typed one.
 */
const SAMPLE_TRIPS: Array<{ origin: string; destination: string }> = [
  { origin: 'Tarneit VIC 3029', destination: 'Docklands VIC 3008' },
  { origin: 'Frankston VIC 3199', destination: 'Clayton VIC 3168' },
  { origin: 'Werribee VIC 3030', destination: 'Carlton VIC 3053' },
  { origin: 'Dandenong VIC 3175', destination: 'Southbank VIC 3006' },
  { origin: 'Geelong VIC 3220', destination: 'Footscray VIC 3011' },
  { origin: 'Craigieburn VIC 3064', destination: 'Richmond VIC 3121' },
  { origin: 'Ballarat VIC 3350', destination: 'Sunshine VIC 3020' },
  { origin: 'Pakenham VIC 3810', destination: 'Box Hill VIC 3128' },
]

/** @returns A sample trip chosen at random for this page view. */
function pickSampleTrip() {
  return SAMPLE_TRIPS[Math.floor(Math.random() * SAMPLE_TRIPS.length)]
}

/** @param value - A "Suburb VIC 1234" sample address. @returns The suburb alone. */
function suburbOf(value: string): string {
  return value.replace(/\s+VIC\s+\d{4}$/, '')
}

/**
 * Build the departure timestamp the sample check uses: the current time,
 * matching the default the trip form offers.
 *
 * @returns An ISO 8601 timestamp with the local UTC offset.
 */
function sampleDepartureTime(): string {
  const date = new Date(Date.now())
  const offsetMinutes = -date.getTimezoneOffset()
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const absolute = Math.abs(offsetMinutes)
  const hours = String(Math.floor(absolute / 60)).padStart(2, '0')
  const minutes = String(absolute % 60).padStart(2, '0')
  const local = new Date(date.getTime() + offsetMinutes * 60_000)
    .toISOString()
    .slice(0, 19)
  return `${local}${sign}${hours}:${minutes}`
}

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
  const navigate = useNavigate()
  const [homeState, setHomeState] = useState<HomeState>(getInitialHomeState)
  // Fixed for the life of this page view, so the label and the check that runs
  // on tap always describe the same trip.
  const [sampleTrip] = useState(pickSampleTrip)
  const [isCheckingSample, setIsCheckingSample] = useState(false)
  const [sampleError, setSampleError] = useState<string | null>(null)

  async function checkSampleTrip() {
    if (isCheckingSample) return
    setSampleError(null)
    setIsCheckingSample(true)
    try {
      const response = await checkTrip({
        origin: sampleTrip.origin,
        destination: sampleTrip.destination,
        departure_time: sampleDepartureTime(),
      })
      saveTripResult(response)
      navigate('/trip/result')
    } catch (requestError) {
      setSampleError(
        requestError instanceof Error
          ? requestError.message
          : 'Something went wrong. Please try again.',
      )
      setIsCheckingSample(false)
    }
  }

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
            <h1>
              {suburbOf(sampleTrip.origin)} <span aria-hidden="true">→</span>{' '}
              {suburbOf(sampleTrip.destination)}
            </h1>
            <p className="home-sample-route">
              {sampleTrip.origin} to {sampleTrip.destination}
            </p>
            {sampleError ? (
              <p className="home-sample-error" role="alert">{sampleError}</p>
            ) : null}
            <button
              className="home-primary-cta"
              type="button"
              onClick={checkSampleTrip}
              disabled={isCheckingSample}
            >
              {isCheckingSample ? 'Checking this trip…' : 'Check this trip →'}
            </button>
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

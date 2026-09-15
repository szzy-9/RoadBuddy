import { Link } from 'react-router-dom'
import TripSearchForm from '../components/TripSearchForm'

/**
 * What a trip check involves, in the order the user experiences it.
 *
 * Each step names something the app actually does, so the promise here matches
 * what the result screen goes on to show.
 */
const STEPS: Array<{ title: string; detail: string }> = [
  {
    title: 'Enter your trip',
    detail: 'Where you are going and when you are leaving',
  },
  {
    title: 'See what is affecting it',
    detail: 'Rain, darkness, speed zones, and the crash history on that stretch of road',
  },
  {
    title: 'Decide before you go',
    detail: 'Compare leaving now against leaving later, then head off knowing what to expect',
  },
]

export default function HomePage() {
  return (
    <div className="home-page page-container">
      <div className="home-grid">
        <div className="home-copy">
          <p className="eyebrow">Before you drive</p>
          <h1>Know what&rsquo;s different about today&rsquo;s drive</h1>
          <p className="lead">
            RoadBuddy looks at the route you are about to take, at the time you are
            about to take it, and tells you what makes this drive more demanding
            than usual
          </p>

          <ol className="what-list">
            {STEPS.map((step, index) => (
              <li key={step.title}>
                <span className="num" aria-hidden="true">{index + 1}</span>
                <span className="what-list-copy">
                  <strong>{step.title}</strong>
                  <span>{step.detail}</span>
                </span>
              </li>
            ))}
          </ol>

          <aside className="not-strip">
            <strong>What RoadBuddy is not</strong> It does not predict crashes, and it
            is never used while driving. Everything it has to say, it says before you
            turn the key
          </aside>
        </div>

        <div className="home-form-column">
          <TripSearchForm
            // title="Check road conditions ahead of time"
            // subtitle="Start here. Your addresses are used for this check only."
            showExample
          />

          <Link className="home-list-card" to="/radar">
            <span className="home-list-icon" aria-hidden="true">🗺️</span>
            <span className="home-list-copy">
              <strong>Risk Radar</strong>
              <small>Map of past crash hotspots around you</small>
            </span>
            <span className="home-list-arrow" aria-hidden="true">→</span>
          </Link>

          <p className="home-refresh-text">Crash data refreshed 12 Aug 2026</p>
        </div>
      </div>
    </div>
  )
}

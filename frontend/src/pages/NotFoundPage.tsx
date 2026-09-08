import { Link } from 'react-router-dom'
import './NotFoundPage.css'

/**
 * Shown for any address the app does not have a screen for.
 *
 * A visible page rather than a silent redirect: quietly landing someone on the
 * home screen hides the fact that the link they followed was wrong, and makes
 * a mistyped address look like the app simply ignored them.
 *
 * @returns The not-found screen.
 */
export default function NotFoundPage() {
  // const { pathname } = useLocation()

  return (
    <div className="not-found-page page-container">
      <section className="card not-found-card">
        <p className="eyebrow">Error</p>
        <h1>We couldn&rsquo;t find that page</h1>
        <p className="not-found-lead">
          It may have moved, or the
          address may have been mistyped.
        </p>

        <Link className="button button-primary not-found-cta" to="/">
          Back to home <span aria-hidden="true">→</span>
        </Link>

        <p className="not-found-alt">
          Or go straight to <Link to="/trip">check a trip</Link> or the{' '}
          <Link to="/radar">Risk Radar</Link>.
        </p>
      </section>
    </div>
  )
}

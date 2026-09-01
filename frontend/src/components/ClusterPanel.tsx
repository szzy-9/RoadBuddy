import type { CrashClusterDetail } from '../types/api'
import ErrorMessage from './ErrorMessage'
import LoadingState from './LoadingState'

interface ClusterPanelProps {
  cluster: CrashClusterDetail | null
  isLoading: boolean
  error: string | null
  onClose: () => void
}

export default function ClusterPanel({ cluster, isLoading, error, onClose }: ClusterPanelProps) {
  if (!cluster && !isLoading && !error) {
    return (
      <aside className="cluster-panel cluster-panel-empty">
        <span className="panel-pin" aria-hidden="true">⌖</span>
        <h2>Select a crash cluster</h2>
        <p>Choose a numbered marker to see the historical conditions recorded there.</p>
      </aside>
    )
  }

  return (
    <aside className="cluster-panel" aria-live="polite">
      <button className="panel-close" type="button" onClick={onClose} aria-label="Close cluster details">×</button>
      {isLoading && <LoadingState message="Loading cluster details…" />}
      {error && <ErrorMessage message={error} />}
      {cluster && !isLoading && (
        <>
          <p className="eyebrow">Historical context</p>
          <h2>Crash cluster</h2>
          <p className="cluster-total">
            <strong>{cluster.crash_count} recorded injury crashes</strong>
            {cluster.first_year && cluster.last_year
              ? ` between ${cluster.first_year} and ${cluster.last_year}`
              : ' in the available dataset'}
          </p>
          <dl className="cluster-facts">
            <div>
              <dt>Young drivers</dt>
              <dd><strong>{cluster.young_driver_crashes}</strong> crashes involved
              a driver aged 16–25
              </dd>
            </div>
            
            <div>
              <dt>Known-age driver crashes</dt>
              <dd>
               <strong>{cluster.eligible_driver_age_crashes}</strong> crashes
              </dd>
            </div>

            <div>
              <dt>Young-driver share</dt>
              <dd>
               {cluster.young_driver_pct_displayable && cluster.young_driver_pct !== null
                 ? `${cluster.young_driver_pct.toFixed(2)}%`
                 : 'Insufficient historical data'}
              </dd>
            </div>
          </dl>
          <p className="panel-note">Historical crash records provide context; they do not predict a future crash.</p>
        </>
      )}
    </aside>
  )
}


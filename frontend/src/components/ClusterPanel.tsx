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
          <p className="eyebrow">Crash history</p>
          <h2>{cluster.name || 'Unnamed location'}</h2>
          <p className="cluster-total">
            <strong>{cluster.crash_count} crashes</strong>
            {cluster.first_year && cluster.last_year
              ? ` between ${cluster.first_year} and ${cluster.last_year}`
              : ' in the available dataset'}
          </p>
          <dl className="cluster-facts">
            <div>
              <dt>Most common</dt>
              <dd>{cluster.dominant_type || 'Not available'}</dd>
            </div>
            <div>
              <dt>Wet road</dt>
              <dd><strong>{cluster.wet_count}</strong> of {cluster.crash_count} crashes</dd>
            </div>
            <div>
              <dt>After dark</dt>
              <dd><strong>{cluster.dark_count}</strong> of {cluster.crash_count} crashes</dd>
            </div>
          </dl>
          <p className="panel-note">Historical crash records provide context; they do not predict a future crash.</p>
        </>
      )}
    </aside>
  )
}


import type { CrashClusterDetail } from '../types/api'
import ErrorMessage from './ErrorMessage'
import LoadingState from './LoadingState'

interface ClusterPanelProps {
  cluster: CrashClusterDetail | null
  isLoading: boolean
  error: string | null
  onClose: () => void
}

/**
 * Build the historical facts shown for a cluster.
 *
 * Each fact is included only when the backend supplied the data behind it, so
 * an older backend, or a cluster whose crashes never recorded a surface or
 * light condition, simply shows fewer lines rather than a zero that would read
 * as "this never happened here".
 *
 * @param cluster - The cluster being described.
 * @returns The facts to render, in display order.
 */
function clusterFacts(
  cluster: CrashClusterDetail,
): Array<{ tone: string; lead: string; rest: string }> {
  const facts: Array<{ tone: string; lead: string; rest: string }> = []

  if (cluster.dominant_crash_type) {
    facts.push({
      tone: 'crash-type',
      lead: `Most were ${cluster.dominant_crash_type.toLowerCase()}`,
      rest: '',
    })
  }
  if (typeof cluster.wet_crashes === 'number') {
    facts.push({
      tone: 'wet',
      lead: `${cluster.wet_crashes} of the ${cluster.crash_count}`,
      rest: ' happened on a wet road',
    })
  }
  if (typeof cluster.dark_crashes === 'number') {
    facts.push({
      tone: 'dark',
      lead: `${cluster.dark_crashes} of the ${cluster.crash_count}`,
      rest: ' happened after dark',
    })
  }

  return facts
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

  const facts = cluster ? clusterFacts(cluster) : []

  return (
    <aside className="cluster-panel" aria-live="polite">
      <button className="panel-close" type="button" onClick={onClose} aria-label="Close cluster details">×</button>
      {isLoading && <LoadingState message="Loading cluster details…" />}
      {error && <ErrorMessage message={error} />}
      {cluster && !isLoading && (
        <>
          <p className="eyebrow">Historical context</p>
          <h2>{cluster.road_name ?? 'Crash cluster'}</h2>
          <p className="cluster-total">
            <strong>{cluster.crash_count} recorded injury crashes</strong>
            {cluster.first_year && cluster.last_year
              ? ` between ${cluster.first_year} and ${cluster.last_year}`
              : ' in the available dataset'}
          </p>
          {facts.length > 0 ? (
            <ul className="cluster-stat-list">
              {facts.map((fact) => (
                <li key={fact.tone} className="cluster-stat">
                  <span className={`cluster-stat-dot cluster-stat-dot-${fact.tone}`} aria-hidden="true" />
                  <span><strong>{fact.lead}</strong>{fact.rest}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="panel-note">
              No crash type, surface or light condition was recorded for this cluster.
            </p>
          )}
          <p className="panel-note">Historical crash records provide context; they do not predict a future crash.</p>
        </>
      )}
    </aside>
  )
}

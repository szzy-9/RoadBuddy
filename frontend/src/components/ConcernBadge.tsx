import type { ConcernLevel } from '../types/api'

const labels: Record<ConcernLevel, string> = {
  low: 'Low concern',
  medium: 'Medium concern',
  higher: 'Higher concern',
}

export default function ConcernBadge({ level }: { level: ConcernLevel }) {
  return <span className={`concern-badge concern-${level}`}>{labels[level]}</span>
}


import type { RiskFactor } from '../types/api'

const factorIcons: Record<RiskFactor['type'], string> = {
  rain: '☂',
  after_dark: '◒',
  high_speed_zone: '↗',
  significant_crash_history: '⌖',
}

export default function RiskFactorCard({ factor }: { factor: RiskFactor }) {
  return (
    <article className="risk-factor-card">
      <span className="factor-icon" aria-hidden="true">{factorIcons[factor.type]}</span>
      <p>{factor.label}</p>
    </article>
  )
}


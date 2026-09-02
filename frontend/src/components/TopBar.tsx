import { useLocation } from 'react-router-dom'

const LABELS: Array<{ path: string; label: string }> = [
  { path: '/radar', label: 'RADAR' },
  { path: '/trip/result', label: 'TRIP RESULT' },
  { path: '/trip', label: 'TRIP' },
  { path: '/learn', label: 'LEARN' },
  { path: '/me', label: 'ME' },
]

function labelForPath(pathname: string): string {
  const match = LABELS.find(
    (item) => pathname === item.path || pathname.startsWith(`${item.path}/`),
  )
  return match ? match.label : 'HOME'
}

export default function TopBar() {
  const { pathname } = useLocation()

  return (
    <header className="top-bar">
      <span className="top-bar-wordmark" aria-label="RoadBuddy">
        <span>road</span><span>buddy</span>
      </span>
      <span className="top-bar-label">{labelForPath(pathname)}</span>
    </header>
  )
}

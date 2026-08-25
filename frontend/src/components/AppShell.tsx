import { Link, Outlet } from 'react-router-dom'
import BottomNav from './BottomNav'

export default function AppShell() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <Link className="brand" to="/" aria-label="RoadBuddy home">
          <span className="brand-mark" aria-hidden="true">RB</span>
          <span>RoadBuddy</span>
        </Link>
        <nav className="desktop-nav" aria-label="Primary navigation">
          <Link to="/">Home</Link>
          <Link to="/radar">Radar</Link>
          <Link className="nav-cta" to="/trip">Check a trip</Link>
        </nav>
      </header>
      <main className="main-content">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}


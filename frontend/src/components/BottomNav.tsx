import { NavLink } from 'react-router-dom'

const items = [
  { to: '/', label: 'Home', path: 'M3 9.5 10 3l7 6.5V17a1 1 0 0 1-1 1h-4v-5H8v5H4a1 1 0 0 1-1-1z' },
  { to: '/radar', label: 'Radar', path: 'M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM10 6v4l3 2' },
  { to: '/trip', label: 'Trip', path: 'M3 13h14M5 13V9l2-4h6l2 4v4M6.5 16.5h1M12.5 16.5h1' },
  { to: '/learn', label: 'Learn', path: 'M10 2a5 5 0 0 0-3 9v2h6v-2a5 5 0 0 0-3-9zM8 16h4' },
  { to: '/me', label: 'Me', path: 'M4 17v-1a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v1M10 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6z' },
]

export default function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Primary navigation">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          aria-label={item.label}
          className={({ isActive }) => (isActive ? 'active' : undefined)}
        >
          <svg className="bottom-nav-icon" viewBox="0 0 20 20" aria-hidden="true">
            <path d={item.path} />
          </svg>
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

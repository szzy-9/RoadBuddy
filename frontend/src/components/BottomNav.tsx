import { NavLink } from 'react-router-dom'

const items = [
  { to: '/', label: 'Home', icon: '⌂' },
  { to: '/radar', label: 'Radar', icon: '◎' },
  { to: '/trip', label: 'Trip', icon: '↗' },
]

export default function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Primary navigation">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          className={({ isActive }) => (isActive ? 'active' : undefined)}
        >
          <span className="bottom-nav-icon" aria-hidden="true">{item.icon}</span>
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}


import { NavLink, useLocation } from 'react-router-dom'
import { isNavItemActive, NAV_ITEMS } from './navItems'

/**
 * Primary navigation for mobile viewports.
 *
 * Hidden by CSS above the desktop breakpoint, where the header nav in
 * {@link TopBar} shows the same destinations.
 *
 * @returns The navigation bar.
 */
export default function BottomNav() {
  const { pathname } = useLocation()

  return (
    <nav className="bottom-nav" aria-label="Primary navigation">
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          data-buddy-target={item.to === '/learn' ? 'learn-nav' : item.to === '/ask' ? 'ask-nav' : undefined}
          aria-label={item.label}
          className={isNavItemActive(item, pathname) ? 'active' : undefined}
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

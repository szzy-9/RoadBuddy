import { NavLink, useLocation } from 'react-router-dom'
import { isNavItemActive, NAV_ITEMS } from './navItems'

/**
 * The sticky site header.
 *
 * Carries the wordmark on every viewport and the primary navigation on
 * desktop; below the mobile breakpoint the nav is hidden here and the bottom
 * nav takes over, so only one set of tabs is ever visible.
 *
 * @returns The header.
 */
export default function TopBar() {
  const { pathname } = useLocation()

  return (
    <header className="top-bar">
      <div className="top-bar-inner">
        <NavLink className="top-bar-wordmark" to="/" aria-label="RoadBuddy home">
          <span>road</span><span>buddy</span>
        </NavLink>

        <nav className="desktop-nav" aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={isNavItemActive(item, pathname) ? 'nav-button active' : 'nav-button'}
            >
              <svg className="nav-icon" viewBox="0 0 20 20" aria-hidden="true">
                <path d={item.path} />
              </svg>
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Balances the wordmark so the nav stays centred on the header.*/}
        <span className="top-bar-note" aria-hidden="true" />
      </div>
    </header>
  )
}

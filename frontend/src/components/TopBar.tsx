import { NavLink, useLocation } from 'react-router-dom'
import { isNavItemActive, NAV_ITEMS } from './navItems'
import { useBuddyGuide } from '../state/BuddyGuideContext'
import koalaReadingIcon from '../assets/koala-reading.png'
import koalaReadingWinkIcon from '../assets/koala-reading-wink.png'

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
  const { openGuide } = useBuddyGuide()

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
              data-buddy-target={item.to === '/learn' ? 'learn-nav' : item.to === '/ask' ? 'ask-nav' : undefined}
              className={isNavItemActive(item, pathname) ? 'nav-button active' : 'nav-button'}
            >
              <svg className="nav-icon" viewBox="0 0 20 20" aria-hidden="true">
                <path d={item.path} />
              </svg>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <button className="buddy-launcher" type="button" aria-label="Meet Buddy" onClick={openGuide}>
          <span className="buddy-launcher-icon" aria-hidden="true">
            <img className="buddy-koala-normal" src={koalaReadingIcon} alt="" draggable="false" />
            <img className="buddy-koala-wink" src={koalaReadingWinkIcon} alt="" draggable="false" />
          </span>
          <span>Buddy</span>
        </button>
      </div>
    </header>
  )
}

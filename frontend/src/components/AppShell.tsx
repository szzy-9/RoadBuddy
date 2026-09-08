import { Suspense } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import BottomNav from './BottomNav'
import ScrollToTop from './ScrollToTop'
import TopBar from './TopBar'

/**
 * Routes that fill the viewport themselves instead of sitting inside the
 * shared page measure.
 *
 * The radar is a map: it should run to the edges of the screen rather than
 * being boxed into the same column as a page of text.
 */
const FULL_BLEED_ROUTES = ['/radar']

export default function AppShell() {
  const { pathname } = useLocation()
  const isFullBleed = FULL_BLEED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  )

  return (
    <div className="app-shell">
      <ScrollToTop />
      <TopBar />
      <main className={isFullBleed ? 'main-content full-bleed' : 'main-content'}>
        <Suspense fallback={<div className="route-loading" role="status">Opening RoadBuddy…</div>}>
          <Outlet />
        </Suspense>
      </main>
      <BottomNav />
    </div>
  )
}

import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import BottomNav from './BottomNav'
import TopBar from './TopBar'

export default function AppShell() {
  return (
    <div className="app-shell">
      <TopBar />
      <main className="main-content">
        <Suspense fallback={<div className="route-loading" role="status">Opening RoadBuddy…</div>}>
          <Outlet />
        </Suspense>
      </main>
      <BottomNav />
    </div>
  )
}

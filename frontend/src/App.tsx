import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import HomePage from './pages/HomePage'

const RadarPage = lazy(() => import('./pages/RadarPage'))
const TripPage = lazy(() => import('./pages/TripPage'))

export default function App() {
  return (
    <Suspense fallback={<div className="route-loading" role="status">Opening RoadBuddy…</div>}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<HomePage />} />
          <Route path="radar" element={<RadarPage />} />
          <Route path="trip" element={<TripPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

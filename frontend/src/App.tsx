import { lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import HomePage from './pages/HomePage'

const RadarPage = lazy(() => import('./pages/RadarPage'))
const TripPage = lazy(() => import('./pages/TripPage'))
const TripResultPage = lazy(() => import('./pages/TripResultPage'))

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="radar" element={<RadarPage />} />
        <Route path="trip" element={<TripPage />} />
        <Route path="trip/result" element={<TripResultPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

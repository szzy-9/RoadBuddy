import { lazy } from 'react'
import { Route, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import HomePage from './pages/HomePage'

const RadarPage = lazy(() => import('./pages/RadarPage'))
const TripPage = lazy(() => import('./pages/TripPage'))
const LearnPage = lazy(() => import('./pages/LearnPage'))
const AskPage = lazy(() => import('./pages/AskPage'))
const MePage = lazy(() => import('./pages/MePage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="radar" element={<RadarPage />} />
        <Route path="trip" element={<TripPage />} />
        {/* The result now lives on /trip itself; kept so existing links and
            any stored history still land somewhere sensible. */}
        {/* <Route path="trip" element={<Navigate to="/trip" replace />} /> */}
        <Route path="learn" element={<LearnPage />} />
        <Route path="ask" element={<AskPage />} />
        <Route path="me" element={<MePage />} />
        {/* Shows a real 404 rather than redirecting home, so a wrong address
            is visible instead of silently swallowed. */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Return to the top of the page on navigation.
 *
 * The router keeps the scroll position across route changes, which was
 * invisible while each screen filled the viewport exactly. Now that pages
 * scroll, arriving at a result part-way down the page reads as a rendering
 * fault, so every navigation starts at the top.
 *
 * @returns Nothing; this component only runs an effect.
 */
export default function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    // 'instant' rather than the root's smooth behaviour: a new screen should
    // already be at the top, not visibly travel there.
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [pathname])

  return null
}

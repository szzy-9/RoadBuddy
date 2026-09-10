import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useBuddyGuide } from '../state/BuddyGuideContext'
import './OnboardingTutorial.css'

const STEPS = [
  { target: 'trip-form', icon: 'M3 13h14M5 13V9l2-4h6l2 4v4M6.5 16.5h1M12.5 16.5h1', title: 'Check a trip', line: 'Route + time → conditions' },
  { target: 'learn-nav', icon: 'M3 4.5c2.3 0 4.3.6 7 2v10c-2.7-1.4-4.7-2-7-2V4.5Zm14 0c-2.3 0-4.3.6-7 2v10c2.7-1.4 4.7-2 7-2V4.5Z', title: 'Practise', line: 'Short source-backed scenarios' },
  { target: 'ask-nav', icon: 'M3 4h14v9H9l-4 3v-3H3V4Z', title: 'Ask Buddy', line: 'Trip or driving questions' },
] as const

type Box = { left: number; top: number; width: number; height: number }
type GuideLayout = {
  spotlight: Box | null
  cardLeft: number
  cardTop: number
  cardWidth: number
  cardMaxHeight: number
}

function findVisibleTarget(name: string): HTMLElement | null {
  return Array.from(document.querySelectorAll<HTMLElement>(`[data-buddy-target="${name}"]`))
    .find((element) => {
      const rect = element.getBoundingClientRect()
      return rect.width > 0 && rect.height > 0
    }) ?? null
}

function viewportBox(): Box {
  const viewport = window.visualViewport
  return {
    left: viewport?.offsetLeft ?? 0,
    top: viewport?.offsetTop ?? 0,
    width: viewport?.width ?? window.innerWidth,
    height: viewport?.height ?? window.innerHeight,
  }
}

function spotlightBox(rect: DOMRect, viewport: Box): Box | null {
  const left = Math.max(viewport.left + 4, rect.left - 6)
  const top = Math.max(viewport.top + 4, rect.top - 6)
  const right = Math.min(viewport.left + viewport.width - 4, rect.right + 6)
  const bottom = Math.min(viewport.top + viewport.height - 4, rect.bottom + 6)
  return right > left && bottom > top
    ? { left, top, width: right - left, height: bottom - top }
    : null
}

function positionCoachmark(spotlight: Box | null, width: number, height: number, viewport: Box) {
  const gap = 12
  const minLeft = viewport.left + gap
  const minTop = viewport.top + gap
  const maxLeft = Math.max(minLeft, viewport.left + viewport.width - width - gap)
  const maxTop = Math.max(minTop, viewport.top + viewport.height - height - gap)
  const clampLeft = (left: number) => Math.max(minLeft, Math.min(left, maxLeft))
  const clampTop = (top: number) => Math.max(minTop, Math.min(top, maxTop))
  if (!spotlight) return { left: maxLeft, top: maxTop }

  const centreLeft = clampLeft(spotlight.left + (spotlight.width - width) / 2)
  const centreTop = clampTop(spotlight.top + (spotlight.height - height) / 2)
  const candidates = [
    { left: spotlight.left + spotlight.width + gap, top: centreTop },
    { left: spotlight.left - width - gap, top: centreTop },
    { left: centreLeft, top: spotlight.top + spotlight.height + gap },
    { left: centreLeft, top: spotlight.top - height - gap },
  ]
  const fitting = candidates.find(({ left, top }) => (
    left >= minLeft && left <= maxLeft && top >= minTop && top <= maxTop
  ))
  if (fitting) return fitting

  // Very short viewports may have no entirely free side. Keep every control
  // reachable, favouring whichever vertical side has more space.
  const below = viewport.top + viewport.height - spotlight.top - spotlight.height
  const above = spotlight.top - viewport.top
  return {
    left: centreLeft,
    top: clampTop(below >= above
      ? spotlight.top + spotlight.height + gap
      : spotlight.top - height - gap),
  }
}

export default function OnboardingTutorial() {
  const { isOpen, currentStep, closeGuide, nextStep, previousStep } = useBuddyGuide()
  const { pathname } = useLocation()
  const cardRef = useRef<HTMLElement>(null)
  const nextRef = useRef<HTMLButtonElement>(null)
  const [layout, setLayout] = useState<GuideLayout | null>(null)
  // openGuide navigates first; wait for the real Home content to be mounted.
  const showGuide = isOpen && pathname === '/'
  const step = STEPS[currentStep]

  useLayoutEffect(() => {
    if (!showGuide) {
      setLayout(null)
      return
    }

    let frame: number | null = null
    let observedTarget: HTMLElement | null = null

    function scheduleMeasure() {
      if (frame !== null) return
      frame = window.requestAnimationFrame(() => {
        frame = null
        measure()
      })
    }

    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(scheduleMeasure)

    function measure() {
      const card = cardRef.current
      if (!card) return
      const viewport = viewportBox()
      const target = findVisibleTarget(step.target)
      if (target !== observedTarget) {
        if (observedTarget) observer?.unobserve(observedTarget)
        observedTarget = target
        if (target) {
          observer?.observe(target)
          const rect = target.getBoundingClientRect()
          if (rect.top < viewport.top || rect.bottom > viewport.top + viewport.height
            || rect.left < viewport.left || rect.right > viewport.left + viewport.width) {
            target.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' })
          }
        }
      }

      const spotlight = target ? spotlightBox(target.getBoundingClientRect(), viewport) : null
      const cardWidth = Math.min(268, Math.max(1, viewport.width - 24))
      const cardMaxHeight = Math.max(1, viewport.height - 24)
      const cardHeight = Math.min(card.getBoundingClientRect().height, cardMaxHeight)
      const position = positionCoachmark(spotlight, cardWidth, cardHeight, viewport)
      setLayout({ spotlight, cardLeft: position.left, cardTop: position.top, cardWidth, cardMaxHeight })
    }

    if (cardRef.current) observer?.observe(cardRef.current)
    observer?.observe(document.documentElement)
    window.addEventListener('resize', scheduleMeasure)
    window.addEventListener('scroll', scheduleMeasure, true)
    window.visualViewport?.addEventListener('resize', scheduleMeasure)
    window.visualViewport?.addEventListener('scroll', scheduleMeasure)
    measure()
    // One frame also catches the router's scroll reset; no polling loop.
    scheduleMeasure()

    return () => {
      if (frame !== null) window.cancelAnimationFrame(frame)
      observer?.disconnect()
      window.removeEventListener('resize', scheduleMeasure)
      window.removeEventListener('scroll', scheduleMeasure, true)
      window.visualViewport?.removeEventListener('resize', scheduleMeasure)
      window.visualViewport?.removeEventListener('scroll', scheduleMeasure)
    }
  }, [showGuide, step])

  useEffect(() => {
    if (!showGuide) return
    const previousFocus = document.activeElement

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeGuide()
      }
      if (event.key !== 'Tab') return
      const controls = Array.from(cardRef.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? [])
      const first = controls[0]
      const last = controls.at(-1)
      if (!first || !last) return
      const focused = document.activeElement
      if (!cardRef.current?.contains(focused)) {
        event.preventDefault()
        ;(event.shiftKey ? last : first).focus()
      } else if (event.shiftKey && focused === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && focused === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      const launcher = document.querySelector<HTMLButtonElement>('[aria-label="Meet Buddy"]')
      if (previousFocus instanceof HTMLElement && previousFocus !== document.body && previousFocus.isConnected) {
        previousFocus.focus({ preventScroll: true })
      } else {
        launcher?.focus({ preventScroll: true })
      }
    }
  }, [showGuide, closeGuide])

  useEffect(() => {
    if (showGuide) nextRef.current?.focus({ preventScroll: true })
  }, [showGuide, currentStep])

  if (!showGuide) return null

  return (
    <div className={`buddy-guide-overlay${layout?.spotlight ? '' : ' without-target'}`}>
      {layout?.spotlight && <div className="buddy-guide-spotlight" style={layout.spotlight} aria-hidden="true" />}
      <section
        ref={cardRef}
        className="buddy-guide-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="buddy-guide-title"
        aria-describedby="buddy-guide-line"
        style={layout ? {
          left: layout.cardLeft, top: layout.cardTop,
          width: layout.cardWidth, maxHeight: layout.cardMaxHeight,
        } : undefined}
      >
        <div className="buddy-guide-copy" aria-live="polite" aria-atomic="true">
          <svg className="buddy-guide-icon" viewBox="0 0 20 20" aria-hidden="true"><path d={step.icon} /></svg>
          <h2 id="buddy-guide-title">{step.title}</h2>
          <p id="buddy-guide-line">{step.line}</p>
        </div>
        <div className="buddy-guide-progress" role="img" aria-label={`Step ${currentStep + 1} of ${STEPS.length}`}>
          {STEPS.map((item, index) => (
            <span key={item.target} className={index === currentStep ? 'active' : undefined} aria-hidden="true" />
          ))}
        </div>
        <div className="buddy-guide-controls">
          <button className="buddy-guide-skip" type="button" onClick={closeGuide}>Skip</button>
          <div>
            <button className="buddy-guide-arrow" type="button" aria-label="Previous step" disabled={currentStep === 0} onClick={previousStep}>
              <span aria-hidden="true">←</span>
            </button>
            <button ref={nextRef} className="buddy-guide-arrow primary" type="button" aria-label={currentStep === STEPS.length - 1 ? 'Finish guide' : 'Next step'} onClick={nextStep}>
              <span aria-hidden="true">{currentStep === STEPS.length - 1 ? '✓' : '→'}</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

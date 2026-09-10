import { useState } from 'react'
import { NAV_ITEMS } from './navItems'
import './OnboardingTutorial.css'
import koalaReadingIcon from '../assets/koala-reading.png'
import koalaReadingWinkIcon from '../assets/koala-reading-wink.png'

const ONBOARDING_SEEN_KEY = 'roadbuddy_onboarding_seen_v1'

const slides = [
  { title: 'Check your trip', description: 'See weather and road risks for your exact trip before you drive.' },
  { title: 'Know the risks', description: 'Use Risk Radar to spot crash hotspots near your route before you drive.' },
]

function shouldShowOnboarding(): boolean {
  try {
    return window.localStorage.getItem(ONBOARDING_SEEN_KEY) === null
  } catch {
    return true
  }
}

function TutorialHand({ className }: { className: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M11 28c-1.7-1.8-3-3.9-3.9-6.2l-1.5-3.7a2.2 2.2 0 0 1 1.2-2.9 2.2 2.2 0 0 1 2.8 1l1.4 2.3V6a2.3 2.3 0 0 1 4.6 0v7.4a2.3 2.3 0 0 1 4.6.2v1a2.3 2.3 0 0 1 4.5.7v1.3a2.3 2.3 0 0 1 4.3 1.2V21c0 2.8-1.1 5.2-3 7H11Z" />
      <path d="M15.6 13.7v3.1M20.2 14.1v3.2M24.7 16.1v2.4" fill="none" />
    </svg>
  )
}

// All screens below are illustrative markup; they never submit or navigate.
function DemoTripForm() {
  return (
    <div className="onboarding-demo-fields">
      <div>From<span>Tarneit VIC 3029</span></div>
      <div>To<span>Docklands VIC 3008</span></div>
      <div>Leaving<span>Today, 15:58</span></div>
      <div className="onboarding-demo-button">Check my trip <b>→</b></div>
      <small>Or load an example trip</small>
    </div>
  )
}

function CheckTripDemo() {
  return (
    <div className="onboarding-demo" role="img" aria-label="Illustrative trip check: enter From, To and Leaving, click Check my trip, then compare a low-concern result for leaving now or later.">
      <div className="onboarding-demo-home" aria-hidden="true"><DemoTripForm /></div>
      <div className="onboarding-demo-trip" aria-hidden="true">
        <div className="onboarding-result-head">
          <small>TODAY · 28 MIN DRIVE</small>
          <strong>About as usual for this route</strong>
          <p>Tarneit → Docklands <b>LOW</b></p>
        </div>
        <div className="onboarding-result-body">
          <strong>What is affecting this trip</strong>
          <p>◇ Historical crash clusters are near the route</p>
          <strong>Would later feel different?</strong>
          <div className="onboarding-departures">
            <div>Leave now<strong>15:58 <b>LOW</b></strong></div>
            <div>Leave later<strong>16:28 <b>LOW</b></strong></div>
          </div>
        </div>
      </div>
      <TutorialHand className="onboarding-hand" />
    </div>
  )
}

function DemoTopNav() {
  return (
    <div className="onboarding-demo-nav">
      <strong className="onboarding-wordmark">road<span>buddy</span></strong>
      <div className="onboarding-demo-nav-items">
        {NAV_ITEMS.map((item) => (
          <div className={`onboarding-demo-nav-item onboarding-demo-nav-${item.label.toLowerCase()}`} key={item.label}>
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d={item.path} /></svg>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Matches the production Radar crash-count bands, without importing its runtime.
const demoBands = [
  { label: '1–4', color: '#2E9E5B' },
  { label: '5–9', color: '#E5B917' },
  { label: '10–19', color: '#E8843C' },
  { label: '20–49', color: '#D6453D' },
  { label: '50+', color: '#A63BC4' },
]

function DemoRoads({ selected = false }: { selected?: boolean }) {
  return (
    <svg className="onboarding-map-roads" viewBox="0 0 260 260" preserveAspectRatio="none" aria-hidden="true">
      <path className="onboarding-map-road-background" d="M-12 38C42 53 78 28 128 42S210 79 278 58M17 275C43 145 76 121 111 86S176 31 204-14M-14 179C52 165 83 193 134 187s81-36 142-23" />
      <path className="onboarding-map-road-secondary" d="M34-8C57 41 52 79 73 157s55 82 71 125M111-10c9 46 44 57 75 78s42 109 52 209" />
      <path className={selected ? 'onboarding-map-road-selected' : 'onboarding-map-road-secondary'} d="M-12 148C37 131 65 113 98 99s65-7 91-27 48-27 86-31" />
    </svg>
  )
}

function RiskRadarDemo() {
  return (
    <div className="onboarding-demo onboarding-radar-demo" role="img" aria-label="Illustrative Risk Radar: click the top Radar tab, search Princes Highway, then select the purple 189-crash cluster to read historical context. Colours represent crash-count bands, not predictions.">
      <div className="onboarding-radar-home" aria-hidden="true">
        <div className="onboarding-radar-home-card">
          <small>BEFORE YOU DRIVE</small>
          <strong>Know what’s different about today’s drive</strong>
          <p>Check conditions before you leave.</p>
          <div className="onboarding-home-steps"><span>1 · Enter your trip</span><span>2 · See what is affecting it</span><span>3 · Decide before you go</span></div>
        </div>
      </div>
      <div className="onboarding-radar-search-screen" aria-hidden="true">
        <DemoRoads />
        <div className="onboarding-radar-search-box">
          <div className="onboarding-radar-input">
            <span className="onboarding-radar-placeholder">Search a suburb, road or postcode</span>
            <span className="onboarding-radar-typed">Princes Highway</span>
          </div>
          <div className="onboarding-radar-suggestion">
            <div><span>⌖</span><span><strong>Princes Highway</strong><small>Mulgrave, VIC, Australia</small></span></div>
            <div><span>⌖</span><span><strong>Princes Highway</strong><small>Clayton, VIC, Australia</small></span></div>
          </div>
        </div>
      </div>
      <div className="onboarding-radar-map" aria-hidden="true">
        <div className="onboarding-radar-map-layer">
          <DemoRoads selected />
          <span className="onboarding-map-road-label">Princes Highway</span>
          <span className="onboarding-cluster onboarding-cluster-6">6</span>
          <span className="onboarding-cluster onboarding-cluster-9">9</span>
          <span className="onboarding-cluster onboarding-cluster-24">24</span>
          <span className="onboarding-cluster onboarding-cluster-189">189</span>
        </div>
        <div className="onboarding-map-legend"><strong>CRASHES</strong>{demoBands.map((band) => <span key={band.label}><i style={{ backgroundColor: band.color }} />{band.label}</span>)}</div>
        <div className="onboarding-cluster-sheet">
          <span className="onboarding-cluster-sheet-close">×</span>
          <small>HISTORICAL CONTEXT</small>
          <strong>Princes Highway</strong>
          <p><b>189 recorded injury crashes</b><br />between 2012 and 2025</p>
          <ul>
            <li><i /><span>Most were <b>right through</b></span></li>
            <li><i /><span><b>29 of the 189</b> happened on a wet road</span></li>
            <li><i /><span><b>57 of the 189</b> happened after dark</span></li>
          </ul>
          <em>Historical crash records provide context; they do not predict a future crash.</em>
        </div>
      </div>
      <div aria-hidden="true"><DemoTopNav /></div>
      <TutorialHand className="onboarding-radar-hand" />
    </div>
  )
}

export default function OnboardingTutorial() {
  const [isOpen, setIsOpen] = useState(shouldShowOnboarding)
  const [slideIndex, setSlideIndex] = useState(0)
  const slide = slides[slideIndex]
  const isFinalSlide = slideIndex === slides.length - 1

  function dismiss() {
    try {
      window.localStorage.setItem(ONBOARDING_SEEN_KEY, 'true')
    } catch {
      // Dismissal still works when browser storage is unavailable.
    }
    setIsOpen(false)
  }

  if (!isOpen) {
    return (
      <button
        className="onboarding-help-button"
        type="button"
        aria-label="Open RoadBuddy tutorial"
        onClick={() => {
          setSlideIndex(0)
          setIsOpen(true)
        }}
      >
        <span className="tutorial-koala-icon" aria-hidden="true">
          <img className="tutorial-koala-image normal-koala" src={koalaReadingIcon} alt="" draggable="false" />
          <img className="tutorial-koala-image wink-koala" src={koalaReadingWinkIcon} alt="" draggable="false" />
        </span>
        <span className="tutorial-launcher-label">Quick Guide</span>
      </button>
    )
  }

  return (
    <div className="onboarding-overlay" role="dialog" aria-modal="true" aria-labelledby="onboarding-title" aria-describedby="onboarding-description">
      <button className="onboarding-skip" type="button" onClick={dismiss}>Skip</button>
      <div className="onboarding-stage">
        <button
          className="onboarding-arrow onboarding-arrow-left"
          type="button"
          aria-label="Previous tutorial page"
          disabled={slideIndex === 0}
          onClick={() => setSlideIndex((current) => Math.max(0, current - 1))}
        >
          ←
        </button>

        <section className={`onboarding-card${isFinalSlide ? ' onboarding-card-final' : ''}`}>
          <div key={slideIndex}>{slideIndex === 0 ? <CheckTripDemo /> : <RiskRadarDemo />}</div>
          <h2 id="onboarding-title">{slide.title}</h2>
          <p id="onboarding-description">{slide.description}</p>
          <div className="onboarding-progress" aria-label={`Tutorial page ${slideIndex + 1} of ${slides.length}`}>
            {slides.map((item, index) => <span className={index === slideIndex ? 'active' : undefined} key={item.title} />)}
          </div>
          {isFinalSlide && (
            <button className="onboarding-confirm" type="button" onClick={dismiss}>Got it — let&apos;s go!</button>
          )}
        </section>

        {!isFinalSlide && (
          <button
            className="onboarding-arrow onboarding-arrow-right"
            type="button"
            aria-label="Next tutorial page"
            onClick={() => setSlideIndex((current) => Math.min(slides.length - 1, current + 1))}
          >
            →
          </button>
        )}
      </div>
    </div>
  )
}

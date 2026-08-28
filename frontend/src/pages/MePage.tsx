import { useState } from 'react'
import { COMPLETED_TOPICS_KEY } from './LearnPage'

const ALL_TOPICS = [
  'Night driving',
  'Wet roads',
  'Freeway merging',
  'Fatigue',
  'Unsealed roads',
  'Wildlife at dusk',
  'Single-lane overtaking',
  'Roundabouts',
  'School zones',
  'Towing',
  'Heavy rain and hail',
]

const SOURCES: Array<[string, string]> = [
  ['Victoria Road Crash Data', 'CC BY 4.0'],
  ['AusRAP star ratings', 'CC BY 4.0'],
  ['Vicmap Speed Zones', 'CC BY 4.0'],
  ['Open-Meteo forecast', 'CC BY 4.0'],
  ['OpenStreetMap', 'ODbL'],
]

const REFRESH_DATE = '12 August 2026'

function readCompletedTopics(): string[] {
  try {
    const stored = window.localStorage.getItem(COMPLETED_TOPICS_KEY)
    return stored ? (JSON.parse(stored) as string[]) : []
  } catch {
    return []
  }
}

export default function MePage() {
  const [completed, setCompleted] = useState<string[]>(readCompletedTopics)

  function clearData() {
    try {
      window.localStorage.removeItem(COMPLETED_TOPICS_KEY)
    } catch {
      // Clearing is best effort; the view still resets below.
    }
    setCompleted([])
  }

  const nextTopic = ALL_TOPICS.find((topic) => !completed.includes(topic))

  return (
    <div className="me-page">
      {/* <header className="page-heading">
        <p className="eyebrow">Me</p>
        <h1>Topics and sources.</h1>
        <p className="lead">
          Topics covered and every dataset we use. No score, no streak, no profile.
        </p>
      </header> */}

      <div className="me-scroll">
        <section className="me-summary">
          <h2>{completed.length} of {ALL_TOPICS.length} topics covered</h2>
          <p>{completed.length > 0 ? completed.join(', ') : 'Nothing covered yet. Start in Learn.'}</p>
        </section>

        <section className="me-panel">
          {ALL_TOPICS.map((topic) => {
            const done = completed.includes(topic)
            return (
              <div className={`me-topic${done ? ' done' : ''}`} key={topic}>
                <span className="me-topic-dot" aria-hidden="true" />
                <span>{topic}</span>
                <span className="me-topic-state">{done ? 'done' : 'not yet'}</span>
              </div>
            )
          })}
        </section>

        {nextTopic && (
          <section className="me-next">
            <h3>Suggested next</h3>
            <p>{nextTopic} · about two minutes</p>
          </section>
        )}

        <p className="me-section-label">Where this comes from</p>
        <section className="me-panel">
          {SOURCES.map(([name, licence]) => (
            <div className="me-source-row" key={name}>
              <span>{name}</span>
              <span className="me-source-licence">{licence}</span>
            </div>
          ))}
          <p className="me-refreshed">Refreshed {REFRESH_DATE}</p>
        </section>

        <section className="me-limit">
          <p className="eyebrow">What we cannot tell you</p>
          <p>
            Whether a road is lit, who is driving, how many passengers are in the car, or
            whether a crash will happen.
          </p>
        </section>

        <button className="me-clear" type="button" onClick={clearData}>
          Clear my data
        </button>

        <p className="me-footnote">
          Lesson text written in our own words from cited sources. A content register records source, licence and date for every card.
        </p>

        <p className="me-disclaimer">
          We are not affiliated with or endorsed by VicRoads, the TAC or DTP.
        </p>
      </div>
    </div>
  )
}

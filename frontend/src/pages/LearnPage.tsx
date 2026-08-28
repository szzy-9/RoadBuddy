import { useState } from 'react'

type Lesson = {
  id: string
  topic: string
  question: string
  options: string[]
  answerIndex: number
  why: string
  source: string
}

const LESSONS: Lesson[] = [
  {
    id: 'wet',
    topic: 'Wet roads',
    question: 'Rain on a 100 zone after dark. What changes first?',
    options: ['Your stopping distance', 'How far your lights reach', 'Nothing, if you stay at the limit'],
    answerIndex: 0,
    why: 'A wet surface stretches your braking distance before anything else about the drive changes. Your headlights reach the same distance wet or dry, so the gap you leave is the thing that has to grow.',
    source: 'VicRoads - driving in wet conditions',
  },
  {
    id: 'night',
    topic: 'Night driving',
    question: 'Driving after dark on an unfamiliar road. What should change first?',
    options: ['Your following distance', 'Your radio volume', 'Nothing, if you know the speed limit'],
    answerIndex: 0,
    why: 'At night you can only react to what your headlights reach. Increasing the gap in front buys back the time your eyes have lost.',
    source: 'VicRoads - night driving',
  },
  {
    id: 'merge',
    topic: 'Freeway merging',
    question: 'Joining a freeway where the on-ramp is short. What matters most?',
    options: ['Matching the speed of traffic before you merge', 'Merging as early as possible', 'Waiting for a very large gap'],
    answerIndex: 0,
    why: 'Most merge crashes involve a speed difference, not a gap that was too small. Matching traffic speed on the ramp means you slot in rather than cut in.',
    source: 'Austroads - merging and lane changing',
  },
  {
    id: 'fatigue',
    topic: 'Fatigue',
    question: 'You are 20 minutes from home after a late shift and feel your eyes getting heavy. What works?',
    options: ['Pulling over for a short rest', 'Opening the window', 'Turning the music up'],
    answerIndex: 0,
    why: 'Air and noise wake you briefly but do nothing for the sleep debt behind the drowsiness. Only rest restores alertness.',
    source: 'TAC - driver fatigue',
  },
]

export const COMPLETED_TOPICS_KEY = 'roadbuddy.completedTopics'

function readCompletedTopics(): string[] {
  try {
    const stored = window.localStorage.getItem(COMPLETED_TOPICS_KEY)
    return stored ? (JSON.parse(stored) as string[]) : []
  } catch {
    return []
  }
}

function addCompletedTopic(topic: string) {
  try {
    const topics = readCompletedTopics()
    if (topics.includes(topic)) return
    window.localStorage.setItem(COMPLETED_TOPICS_KEY, JSON.stringify([...topics, topic]))
  } catch {
    // Progress is a convenience only, so the lesson still works without storage.
  }
}

export default function LearnPage() {
  const [lessonIndex, setLessonIndex] = useState(0)
  const [answered, setAnswered] = useState<number | null>(null)
  const [saved, setSaved] = useState(false)

  const lesson = LESSONS[lessonIndex]
  const isCorrect = answered === lesson.answerIndex

  function chooseOption(index: number) {
    if (answered !== null) return
    setAnswered(index)
  }

  function completeLesson() {
    addCompletedTopic(lesson.topic)
    setSaved(true)
  }

  function nextLesson() {
    setLessonIndex((current) => (current + 1) % LESSONS.length)
    setAnswered(null)
    setSaved(false)
  }

  return (
    <div className="learn-page">
      {/* <header className="page-heading">
        <p className="eyebrow">Street smarts</p>
        <h1>One question, one reason why.</h1>
        <p className="lead">About two minutes, and no score to chase.</p>
      </header> */}

      <div className="learn-scroll">
        <section className="learn-question">
          <span className="learn-pill">{lesson.topic}</span>
          <h2>{lesson.question}</h2>
          <div className="learn-options">
            {lesson.options.map((option, index) => {
              const state = answered === null
                ? ''
                : index === lesson.answerIndex
                  ? ' correct'
                  : index === answered
                    ? ' incorrect'
                    : ''

              return (
                <button
                  key={option}
                  className={`learn-option${state}`}
                  type="button"
                  onClick={() => chooseOption(index)}
                  disabled={answered !== null}
                >
                  {option}
                </button>
              )
            })}
          </div>
        </section>

        {answered !== null && (
          <>
            <section className={`learn-verdict ${isCorrect ? 'is-correct' : 'is-incorrect'}`} aria-live="polite">
              <h3>
                {isCorrect
                  ? lesson.options[lesson.answerIndex]
                  : `Not quite - it is ${lesson.options[lesson.answerIndex].toLowerCase()}`}
              </h3>
              <p>
                {isCorrect
                  ? 'That is the one that moves first.'
                  : 'Here is why that one matters most.'}
              </p>
            </section>

            <section className="learn-why">
              <p className="eyebrow">Why</p>
              <p>{lesson.why}</p>
              <div className="learn-source">
                <p className="eyebrow">Source</p>
                <strong>{lesson.source}</strong>
              </div>
            </section>

            <div className="learn-actions">
              <button className="button button-primary" type="button" onClick={completeLesson} disabled={saved}>
                {saved ? 'Added to my topics' : 'Add to my topics →'}
              </button>
              <button className="text-button" type="button" onClick={nextLesson}>
                Next lesson
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

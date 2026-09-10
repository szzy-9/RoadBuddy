import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import buddyKoala from '../assets/koala-reading.png'
import { classifyBuddyQuestion, getBuddyAnswer } from '../data/buddyAnswers'
import type { BuddyAnswer, BuddyIntent } from '../data/buddyAnswers'
import { LESSONS } from '../data/lessons'
import { useTripResult } from '../state/tripResult'
import './AskPage.css'

const TOPIC_ORDER = ['night', 'wet', 'merge', 'fatigue'] as const
const SUGGESTED_TOPICS = TOPIC_ORDER.flatMap((id) => LESSONS.filter((lesson) => lesson.id === id))
const ANSWER_ICON_PATHS: Record<string, string> = {
  book: 'M3 4.5c2.3 0 4.3.6 7 2v10c-2.7-1.4-4.7-2-7-2V4.5Zm14 0c-2.3 0-4.3.6-7 2v10c2.7-1.4 4.7-2 7-2V4.5Z',
  shield: 'M10 2 3 5v5c0 4 7 8 7 8s7-4 7-8V5l-7-3Z',
  route: 'M5 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm10 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM5 7v3h10v3',
}

export default function AskPage() {
  const [tripResult] = useTripResult()
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<BuddyAnswer | null>(null)

  // Keep a visible trip answer tied to the current store, even if it changes
  // while this page is open. There is no separate trip snapshot or history.
  const currentAnswer = answer?.intent === 'trip' ? getBuddyAnswer('trip', tripResult) : answer

  function ask(intent: BuddyIntent) {
    setAnswer(getBuddyAnswer(intent, tripResult))
    setQuestion('')
  }

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!question.trim()) return
    ask(classifyBuddyQuestion(question, tripResult))
  }

  return (
    <div className="ask-page">
      <header className="ask-header">
        <img src={buddyKoala} alt="" width="72" height="72" />
        <h1>Buddy</h1>
      </header>

      <div className="ask-suggestions" role="group" aria-label="Suggested questions">
        {tripResult && (
          <button className="ask-chip" type="button" onClick={() => ask('trip')}>
            <span aria-hidden="true">◉</span> This trip
          </button>
        )}
        {SUGGESTED_TOPICS.map((lesson) => (
          <button className="ask-chip" type="button" key={lesson.id} onClick={() => ask(lesson.id)}>
            <span aria-hidden="true">{lesson.icon}</span> {lesson.shortLabel}
          </button>
        ))}
      </div>

      <div className="ask-answer-region" role="status" aria-live="polite" aria-atomic="true">
        {currentAnswer && (
          <article className="ask-answer" aria-labelledby="ask-answer-heading">
            <div className="ask-answer-icon" aria-hidden="true">
              {ANSWER_ICON_PATHS[currentAnswer.icon] ? (
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d={ANSWER_ICON_PATHS[currentAnswer.icon]} />
                </svg>
              ) : currentAnswer.icon}
            </div>
            <h2 id="ask-answer-heading">{currentAnswer.heading}</h2>
            {currentAnswer.factors.length > 0 && (
              <ul className="ask-factors">
                {currentAnswer.factors.map((factor) => (
                  <li key={factor.type}><span aria-hidden="true">{factor.icon}</span> {factor.label}</li>
                ))}
              </ul>
            )}
            <p>{currentAnswer.body}</p>
            {(currentAnswer.sources.length > 0 || currentAnswer.actions.length > 0) && (
              <div className="ask-answer-links">
                {currentAnswer.sources.map((source) => (
                  <a className="ask-source" key={source.href} href={source.href} target="_blank" rel="noreferrer">
                    <span aria-hidden="true">↗</span> {source.name}
                  </a>
                ))}
                {currentAnswer.actions.map((action) => (
                  <Link className="ask-action" key={action.to} to={action.to}>
                    <span aria-hidden="true">{action.icon}</span> {action.label}
                  </Link>
                ))}
              </div>
            )}
          </article>
        )}
      </div>

      <form className="ask-form" onSubmit={submitQuestion}>
        <input
          aria-label="Ask Buddy"
          placeholder="Ask Buddy..."
          autoComplete="off"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button type="submit" aria-label="Send question" disabled={!question.trim()}>
          <span aria-hidden="true">➤</span>
        </button>
      </form>
    </div>
  )
}

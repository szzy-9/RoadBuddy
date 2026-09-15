import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import buddyKoala from '../assets/koala-reading.png'
import { classifyBuddyQuestion, getBuddyAnswer } from '../data/buddyAnswers'
import type { BuddyAnswer, BuddyIntent } from '../data/buddyAnswers'
import { LESSONS } from '../data/lessons'
import { PREPARED_QUESTIONS } from '../data/preparedQuestions'
import type { PreparedQuestion } from '../data/preparedQuestions'
import { useTripResult } from '../state/tripResult'
import './AskPage.css'

const TOPIC_ORDER = ['night', 'wet', 'merge', 'fatigue'] as const
const SUGGESTED_TOPICS = TOPIC_ORDER.flatMap((id) => LESSONS.filter((lesson) => lesson.id === id))
const ADDITIONAL_TOPICS = [
  { id: 'road-rules', icon: '🚦', shortLabel: 'Road rules' },
  { id: 'p1', icon: 'P1', shortLabel: 'P1 rules' },
] as const
const ANSWER_ICON_PATHS: Record<string, string> = {
  book: 'M3 4.5c2.3 0 4.3.6 7 2v10c-2.7-1.4-4.7-2-7-2V4.5Zm14 0c-2.3 0-4.3.6-7 2v10c2.7-1.4 4.7-2 7-2V4.5Z',
  shield: 'M10 2 3 5v5c0 4 7 8 7 8s7-4 7-8V5l-7-3Z',
  route: 'M5 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm10 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM5 7v3h10v3',
}

function P1Icon() {
  return (
    <svg className="ask-topic-svg" aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="4" width="16" height="12" rx="2" />
      <circle cx="7" cy="8.5" r="1.5" />
      <path d="M4.5 13c0-3 5-3 5 0M12 8h3M12 12h3" />
    </svg>
  )
}

export default function AskPage() {
  const [tripResult] = useTripResult()
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<BuddyAnswer | null>(null)
  const [moreTopicsOpen, setMoreTopicsOpen] = useState(false)

  // Keep a visible trip answer tied to the current store, even if it changes
  // while this page is open. There is no separate trip snapshot or history.
  const currentAnswer = answer?.intent === 'trip' ? getBuddyAnswer('trip', tripResult) : answer
  const secondaryTopicActive = ADDITIONAL_TOPICS.some((topic) => topic.id === currentAnswer?.intent)
  const secondaryTopicsVisible = moreTopicsOpen || secondaryTopicActive

  function ask(intent: BuddyIntent) {
    setAnswer(getBuddyAnswer(intent, tripResult))
    setQuestion('')
  }

  function askPrepared(prepared: PreparedQuestion) {
    if (prepared.requiresTripContext) return
    setAnswer({
      intent: prepared.topic,
      icon: ADDITIONAL_TOPICS.find((topic) => topic.id === prepared.topic)?.icon ?? (prepared.topic === 'fatigue' ? '◷' : prepared.topic === 'merge' ? '↗' : prepared.topic === 'wet' ? '☂' : '☾'),
      heading: prepared.question,
      body: prepared.answer,
      sources: prepared.sources,
      factors: [],
      actions: [],
    })
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
        <button
          className="ask-chip ask-topics-toggle"
          type="button"
          aria-expanded={secondaryTopicsVisible}
          aria-controls="ask-secondary-topics"
          disabled={secondaryTopicActive}
          title={secondaryTopicActive ? 'Select a primary topic before collapsing this row' : undefined}
          onClick={() => setMoreTopicsOpen((open) => !open)}
        >
          {secondaryTopicsVisible ? 'Less' : 'More'}
          <svg className="ask-topic-svg" aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d={secondaryTopicsVisible ? 'm6 12 4-4 4 4' : 'm6 8 4 4 4-4'} />
          </svg>
        </button>
        <div id="ask-secondary-topics" className="ask-secondary-topics" role="group" aria-label="More topics" hidden={!secondaryTopicsVisible}>
        {ADDITIONAL_TOPICS.map((topic) => (
          <button className="ask-chip" type="button" key={topic.id} onClick={() => {
            setMoreTopicsOpen(true)
            setAnswer({ intent: topic.id, icon: topic.icon, heading: topic.shortLabel, body: 'Choose a question below the topic buttons.', sources: [], factors: [], actions: [] })
            setQuestion('')
          }}>
            {topic.id === 'p1' ? (
              <P1Icon />
            ) : <span aria-hidden="true">{topic.icon}</span>} {topic.shortLabel}
          </button>
        ))}
        </div>
      </div>

      <div className="ask-answer-region" role="status" aria-live="polite" aria-atomic="true">
        {(currentAnswer?.intent === 'night' || currentAnswer?.intent === 'wet' || currentAnswer?.intent === 'merge' || currentAnswer?.intent === 'fatigue' || currentAnswer?.intent === 'road-rules' || currentAnswer?.intent === 'p1') && (
          <div className="ask-prepared-questions" role="group" aria-label={currentAnswer.intent === 'p1' ? 'P1 rules questions' : currentAnswer.intent === 'road-rules' ? 'Road rules questions' : currentAnswer.intent === 'fatigue' ? 'Tired driving questions' : currentAnswer.intent === 'merge' ? 'Merge driving questions' : currentAnswer.intent === 'wet' ? 'Wet driving questions' : 'Night driving questions'}>
            {PREPARED_QUESTIONS.filter((prepared) => prepared.topic === currentAnswer.intent && !prepared.requiresTripContext).map((prepared) => (
              <button className="ask-chip" type="button" key={prepared.id} onClick={() => askPrepared(prepared)}>
                {prepared.question}
              </button>
            ))}
          </div>
        )}
        {currentAnswer && (
          <article className="ask-answer" aria-labelledby="ask-answer-heading">
            <div className="ask-answer-icon" aria-hidden="true">
              {currentAnswer.intent === 'p1' ? <P1Icon /> : ANSWER_ICON_PATHS[currentAnswer.icon] ? (
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
            {currentAnswer.body.split('\n\n').map((paragraph, index) => (
              <p key={index}>
                {paragraph.split(/(\*\*[^*]+\*\*)/g).map((part, partIndex) => (
                  part.startsWith('**') && part.endsWith('**') && part.length > 4
                    ? <strong key={partIndex}>{part.slice(2, -2)}</strong>
                    : part
                ))}
              </p>
            ))}
            {currentAnswer.sources.length > 0 && <h3 className="ask-sources-heading">Sources</h3>}
            {(currentAnswer.sources.length > 0 || currentAnswer.actions.length > 0) && (
              <div className="ask-answer-links">
                {currentAnswer.sources.map((source) => (
                  <a className="ask-source" key={source.href} href={source.href} target="_blank" rel="noopener noreferrer">
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

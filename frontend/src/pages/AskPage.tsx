import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { askBuddy } from '../api/client'
import buddyKoala from '../assets/koala-reading.png'
import { getBuddyAnswer } from '../data/buddyAnswers'
import type { BuddyAnswer } from '../data/buddyAnswers'
import { LESSONS } from '../data/lessons'
import { PREPARED_QUESTIONS } from '../data/preparedQuestions'
import type { PreparedQuestion } from '../data/preparedQuestions'
import { useTripResult } from '../state/tripResult'
import type { AskSource } from '../types/api'
import './AskPage.css'

const TOPIC_ORDER = ['night', 'wet', 'merge', 'fatigue'] as const
const SUGGESTED_TOPICS = TOPIC_ORDER.flatMap((id) => LESSONS.filter((lesson) => lesson.id === id))

// Topics that have no lesson in `lessons.ts`, so they are not in
// SUGGESTED_TOPICS. Kept behind the More toggle to hold the primary row to
// one line at phone width.
const ADDITIONAL_TOPICS = [
  { id: 'road-rules', icon: '🚦', shortLabel: 'Road rules' },
  { id: 'p1', icon: 'P1', shortLabel: 'P1 rules' },
] as const

type TopicId = PreparedQuestion['topic']

const TOPIC_QUESTION_GROUP_LABELS: Record<TopicId, string> = {
  night: 'Night driving questions',
  wet: 'Wet driving questions',
  merge: 'Merge driving questions',
  fatigue: 'Tired driving questions',
  'road-rules': 'Road rules questions',
  p1: 'P1 rules questions',
}

/** Heading and icon for the card shown when a topic is picked. */
const TOPIC_CARDS: Record<TopicId, { heading: string; icon: string }> = {
  night: { heading: 'Night driving', icon: '☾' },
  wet: { heading: 'Wet roads', icon: '☂' },
  merge: { heading: 'Freeway merging', icon: '↗' },
  fatigue: { heading: 'Fatigue', icon: '◷' },
  'road-rules': { heading: 'Road rules', icon: '🚦' },
  p1: { heading: 'P1 rules', icon: 'P1' },
}

// The API names each source in full. Shortened here so two citations sit
// on one row at phone width instead of stacking; the full names are long
// enough that "Road Safety Road Rules 2017" plus "Road to Solo Driving
// handbook" overflow a single line by a few pixels.
const SOURCE_LABELS: Record<string, string> = {
  'Road to Solo Driving handbook': 'Road to Solo Driving',
  'Road Safety Road Rules 2017': 'Road Rules 2017',
}

const ANSWER_ICON_PATHS: Record<string, string> = {
  book: 'M3 4.5c2.3 0 4.3.6 7 2v10c-2.7-1.4-4.7-2-7-2V4.5Zm14 0c-2.3 0-4.3.6-7 2v10c2.7-1.4 4.7-2 7-2V4.5Z',
  shield: 'M10 2 3 5v5c0 4 7 8 7 8s7-4 7-8V5l-7-3Z',
  route: 'M5 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm10 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM5 7v3h10v3',
}

/** Renders the `**bold**` spans the prepared answers and corpus replies use. */
function RichText({ text }: { text: string }) {
  return (
    <>
      {text.split('\n\n').map((paragraph, index) => (
        <p key={index}>
          {paragraph.split(/(\*\*[^*]+\*\*)/g).map((part, partIndex) => (
            part.startsWith('**') && part.endsWith('**') && part.length > 4
              ? <strong key={partIndex}>{part.slice(2, -2)}</strong>
              : part
          ))}
        </p>
      ))}
    </>
  )
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

/** An answer retrieved from the road-safety corpus by the Ask endpoint. */
type SourcedAnswer = {
  kind: 'sourced'
  question: string
  answer: string
  answered: boolean
  sources: AskSource[]
  /** Offered questions, sent with a greeting. */
  examples: string[]
  /** A greeting is answered conversationally, not from the corpus. */
  isGreeting: boolean
}

/** The trip answer, which is assembled locally from the last trip check. */
type TripAnswer = { kind: 'trip' }

/**
 * A topic card. Picking a topic offers its prepared questions rather than
 * asking anything, so the corpus is only queried once a real question is
 * chosen.
 */
type TopicPrompt = { kind: 'topic'; topic: TopicId }

type AskState = SourcedAnswer | TripAnswer | TopicPrompt | null

export default function AskPage() {
  const [tripResult] = useTripResult()
  const [question, setQuestion] = useState('')
  const [state, setState] = useState<AskState>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Which topic's prepared questions are on offer. Held past the topic card
  // itself so the list stays up while you read the answer you picked.
  const [selectedTopic, setSelectedTopic] = useState<TopicId | null>(null)
  const [moreTopicsOpen, setMoreTopicsOpen] = useState(false)

  // Only the newest question may render. Without this an earlier, slower
  // answer can land after a later one and overwrite it.
  const requestId = useRef(0)

  // The trip answer reads from the live trip store rather than a snapshot,
  // so it stays correct if the trip check changes while this page is open.
  const tripAnswer: BuddyAnswer | null =
    state?.kind === 'trip' ? getBuddyAnswer('trip', tripResult) : null

  const secondaryTopicActive = ADDITIONAL_TOPICS.some((topic) => topic.id === selectedTopic)
  const secondaryTopicsVisible = moreTopicsOpen || secondaryTopicActive

  // Contextual entries need a trip that has been checked, so they are listed
  // only once one is in the store.
  const preparedForTopic = selectedTopic
    ? PREPARED_QUESTIONS.filter((prepared) => (
      prepared.topic === selectedTopic && (!prepared.requiresTripContext || tripResult !== null)
    ))
    : []

  function showTrip() {
    requestId.current += 1
    setPending(false)
    setError(null)
    setState({ kind: 'trip' })
    setSelectedTopic(null)
    setQuestion('')
  }

  async function askCorpus(text: string) {
    const id = (requestId.current += 1)
    setPending(true)
    setError(null)
    setQuestion('')

    try {
      const response = await askBuddy({ question: text })
      if (id !== requestId.current) return
      setState({
        kind: 'sourced',
        question: text,
        answer: response.answer,
        answered: response.answered,
        sources: response.sources,
        examples: response.examples ?? [],
        isGreeting: response.reason === 'greeting',
      })
    } catch (caught) {
      if (id !== requestId.current) return
      setError(caught instanceof Error ? caught.message : 'Buddy could not answer just now.')
      setState(null)
    } finally {
      if (id === requestId.current) setPending(false)
    }
  }

  // Picking a topic only offers its questions. Nothing is asked until one of
  // them is chosen, so no request goes out here.
  function selectTopic(topic: TopicId) {
    requestId.current += 1
    setPending(false)
    setError(null)
    setSelectedTopic(topic)
    setState({ kind: 'topic', topic })
    setQuestion('')
  }

  // A prepared question is asked against the corpus like any other, so the
  // answer stays sourced from the backend rather than from the bundle.
  function askPrepared(prepared: PreparedQuestion) {
    void askCorpus(prepared.question)
  }

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = question.trim()
    if (!text || pending) return
    setSelectedTopic(null)
    void askCorpus(text)
  }

  return (
    <div className="ask-page">
      <header className="ask-header">
        <img src={buddyKoala} alt="" width="72" height="72" />
        <h1>Buddy</h1>
      </header>

      <div className="ask-suggestions" role="group" aria-label="Suggested questions">
        {tripResult && (
          <button className="ask-chip" type="button" onClick={showTrip} disabled={pending}>
            <span aria-hidden="true">◉</span> This trip
          </button>
        )}
        {SUGGESTED_TOPICS.map((lesson) => (
          <button
            className="ask-chip"
            type="button"
            key={lesson.id}
            disabled={pending}
            onClick={() => selectTopic(lesson.id as TopicId)}
          >
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
            <button
              className="ask-chip"
              type="button"
              key={topic.id}
              disabled={pending}
              onClick={() => {
                setMoreTopicsOpen(true)
                selectTopic(topic.id)
              }}
            >
              {topic.id === 'p1' ? (
                <P1Icon />
              ) : <span aria-hidden="true">{topic.icon}</span>} {topic.shortLabel}
            </button>
          ))}
        </div>
      </div>

      <div className="ask-answer-region" role="status" aria-live="polite" aria-atomic="true">
        {selectedTopic && preparedForTopic.length > 0 && (
          <div className="ask-prepared-questions" role="group" aria-label={TOPIC_QUESTION_GROUP_LABELS[selectedTopic]}>
            {preparedForTopic.map((prepared) => (
              <button
                className="ask-chip"
                type="button"
                key={prepared.id}
                disabled={pending}
                onClick={() => askPrepared(prepared)}
              >
                {prepared.question}
              </button>
            ))}
          </div>
        )}

        {pending && (
          <p className="ask-pending">
            <span className="ask-spinner" aria-hidden="true" /> Buddy is checking the handbook...
          </p>
        )}

        {!pending && error && <p className="ask-error">{error}</p>}

        {!pending && !error && state?.kind === 'topic' && (
          <article className="ask-answer ask-topic-card" aria-labelledby="ask-answer-heading">
            <div className="ask-answer-icon" aria-hidden="true">
              {state.topic === 'p1' ? <P1Icon /> : TOPIC_CARDS[state.topic].icon}
            </div>
            <h2 id="ask-answer-heading">{TOPIC_CARDS[state.topic].heading}</h2>
            <p>Pick one of the questions above, or type your own below.</p>
          </article>
        )}

        {!pending && !error && state?.kind === 'sourced' && (
          <article
            className={state.answered ? 'ask-answer' : 'ask-answer ask-answer-declined'}
            data-greeting={state.isGreeting ? 'true' : undefined}
            aria-labelledby="ask-answer-heading"
          >
            <div className="ask-answer-icon" aria-hidden="true">
              {selectedTopic === 'p1' ? <P1Icon /> : (
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d={ANSWER_ICON_PATHS.book} />
                </svg>
              )}
            </div>
            <h2 id="ask-answer-heading">{state.isGreeting ? state.answer : state.question}</h2>
            {!state.isGreeting && <RichText text={state.answer} />}
            {state.examples.length > 0 && (
              <>
                <p className="ask-examples-lead">Here are some example questions:</p>
                <ul className="ask-examples">
                  {state.examples.map((example) => (
                    <li key={example}>
                      <button type="button" onClick={() => void askCorpus(example)}>
                        {example}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
            {state.sources.length > 0 && (
              <>
                <h3 className="ask-sources-heading">Sources</h3>
                <div className="ask-answer-links">
                  {state.sources.map((source) => (
                    <span className="ask-source" key={source.name}>
                      <span aria-hidden="true">▤</span> {SOURCE_LABELS[source.name] ?? source.name}
                    </span>
                  ))}
                </div>
              </>
            )}
          </article>
        )}

        {!pending && !error && tripAnswer && (
          <article className="ask-answer" aria-labelledby="ask-answer-heading">
            <div className="ask-answer-icon" aria-hidden="true">
              {ANSWER_ICON_PATHS[tripAnswer.icon] ? (
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d={ANSWER_ICON_PATHS[tripAnswer.icon]} />
                </svg>
              ) : tripAnswer.icon}
            </div>
            <h2 id="ask-answer-heading">{tripAnswer.heading}</h2>
            {tripAnswer.factors.length > 0 && (
              <ul className="ask-factors">
                {tripAnswer.factors.map((factor) => (
                  <li key={factor.type}><span aria-hidden="true">{factor.icon}</span> {factor.label}</li>
                ))}
              </ul>
            )}
            <p>{tripAnswer.body}</p>
            {(tripAnswer.sources.length > 0 || tripAnswer.actions.length > 0) && (
              <div className="ask-answer-links">
                {tripAnswer.sources.map((source) => (
                  <a className="ask-source" key={source.href} href={source.href} target="_blank" rel="noopener noreferrer">
                    <span aria-hidden="true">↗</span> {source.name}
                  </a>
                ))}
                {tripAnswer.actions.map((action) => (
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
        <button type="submit" aria-label="Send question" disabled={!question.trim() || pending}>
          <span aria-hidden="true">➤</span>
        </button>
      </form>
    </div>
  )
}

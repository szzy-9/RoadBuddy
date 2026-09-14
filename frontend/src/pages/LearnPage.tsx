import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'

import { addCompletedTopics, getLessonFeedback, getTripLessonIds, LESSONS } from '../data/lessons'
import type { Lesson } from '../data/lessons'
import { useTripResult } from '../state/tripResult'
import './LearnPage.css'
import { checkLearnAnswer, getLearnQuestions, getLearnTopics, getMockTest, gradeMockTest } from '../api/client'
import { getMockTestAnswers } from '../lib/learnPractice'

import type {
  LearnAnswerResponse, LearnSource, LearnTopic, MockTestGradeResponse,
  MockTestQuestion, TripLessonResponse,
} from '../types/api'

type PracticeSession = {
  lessons: Lesson[]
  questionIndex: number
  answers: number[]
  finished: boolean
}

type TripAnswerState = {
  selectedOption: string
  correct: boolean
  correctOption: string
  explanation: string
  sourceName: string
  sourceUrl: string | null
}

type TripPracticeState = {
  questionIndex: number
  answers: Record<string, TripAnswerState>
  finished: boolean
}

export default function LearnPage() {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const [tripResult] = useTripResult()
  
  const tripLesson = (
    location.state as { tripLesson?: TripLessonResponse } | null
  )?.tripLesson ?? null
  
  const tripLessonIds = !tripLesson && searchParams.get('mode') === 'trip' && tripResult
    ? getTripLessonIds(tripResult.factors)
    : []

  // Reset on a different trip match or a return to /learn, without a landing
  // screen flash before trip practice. This remains the same quiz UI.
    
  if (
    searchParams.get('mode') === 'trip'
    && tripLesson
    && tripLesson.available
    && tripLesson.questions.length > 0
  ) {
    return (
      <TripLearnPractice
        key={tripLesson.questions.map((question) => question.id).join(',')}
        tripLesson={tripLesson}
      />
    )
  }

  if (searchParams.get('mode') === 'trip' && tripLesson) {
    return (
      <div className="learn-page">
        <p role="status">Trip preparation questions are currently unavailable.</p>
        <Link className="button button-secondary" to="/learn">Back to Learn</Link>
      </div>
    )
  }

  if (tripLessonIds.length > 0) {
    return <LegacyTripPractice key={tripLessonIds.join(',')} tripLessonIds={tripLessonIds} />
  }

  return <LearnBankPractice key={location.key} />
}

function LearnSourceReference({ source }: { source: Pick<LearnSource, 'name' | 'url'> }) {
  return source.url !== null ? (
    <a className="learn-source" href={source.url} target="_blank" rel="noreferrer">
      <span aria-hidden="true">↗</span> {source.name}
    </a>
  ) : <span className="learn-source">{source.name}</span>
}

type BankMode =
  | { kind: 'topic'; topic: LearnTopic }
  | { kind: 'quick' }
  | { kind: 'mock' }

type BankSession = {
  mode: BankMode
  questions: MockTestQuestion[]
  totalQuestions: number
  passMarkPercent: number | null
  questionIndex: number
  selectedOptions: Record<string, string>
  feedback: Record<string, LearnAnswerResponse>
  grade: MockTestGradeResponse | null
  finished: boolean
}

function LearnBankPractice() {
  const [topics, setTopics] = useState<LearnTopic[] | null>(null)
  const [topicsError, setTopicsError] = useState<string | null>(null)
  const [topicsAttempt, setTopicsAttempt] = useState(0)
  const [session, setSession] = useState<BankSession | null>(null)
  const [loadMode, setLoadMode] = useState<BankMode | null>(null)
  const [loading, setLoading] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestVersion = useRef(0)
  const pendingRef = useRef(false)
  const questionHeading = useRef<HTMLHeadingElement>(null)
  const launcherButton = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    let cancelled = false
    setTopics(null)
    setTopicsError(null)
    getLearnTopics().then((response) => {
      if (!cancelled) setTopics(response.topics)
    }).catch((cause: unknown) => {
      if (!cancelled) setTopicsError(cause instanceof Error ? cause.message : 'Could not load topics.')
    })
    return () => { cancelled = true }
  }, [topicsAttempt])

  useEffect(() => () => { requestVersion.current += 1 }, [])

  useEffect(() => {
    if (session) questionHeading.current?.focus()
    else if (!loadMode) launcherButton.current?.focus()
  }, [session?.questionIndex, session?.finished, loadMode])

  function backToLearn() {
    requestVersion.current += 1
    pendingRef.current = false
    setPending(false)
    setSession(null)
    setLoadMode(null)
    setLoading(false)
    setError(null)
  }

  async function startPractice(mode: BankMode) {
    const version = ++requestVersion.current
    pendingRef.current = false
    setPending(false)
    setLoadMode(mode)
    setSession(null)
    setError(null)
    setLoading(true)
    try {
      let questions: MockTestQuestion[]
      let totalQuestions: number
      let passMarkPercent: number | null = null
      if (mode.kind === 'topic') {
        const response = await getLearnQuestions(mode.topic.id)
        questions = response.questions
        totalQuestions = questions.length
      } else {
        const response = await getMockTest()
        questions = mode.kind === 'quick' ? response.questions.slice(0, 3) : response.questions
        totalQuestions = mode.kind === 'mock' ? response.total_questions : questions.length
        if (mode.kind === 'mock') passMarkPercent = response.pass_mark_percent
      }
      if (version !== requestVersion.current) return
      if (questions.length === 0) {
        setError('No questions are currently available for this activity. Please try again later.')
        return
      }
      setSession({
        mode, questions, totalQuestions, passMarkPercent, questionIndex: 0,
        selectedOptions: {}, feedback: {}, grade: null, finished: false,
      })
    } catch (cause) {
      if (version === requestVersion.current) {
        setError(cause instanceof Error ? cause.message : 'Could not load questions. Please try again.')
      }
    } finally {
      if (version === requestVersion.current) setLoading(false)
    }
  }

  async function chooseOption(optionKey: string) {
    if (!session || session.finished || pendingRef.current) return
    const question = session.questions[session.questionIndex]
    if (session.feedback[question.id]) return
    setError(null)
    setSession((current) => current && ({
      ...current, selectedOptions: { ...current.selectedOptions, [question.id]: optionKey },
    }))
    // Mock tests reveal answers only after the complete test is graded.
    if (session.mode.kind === 'mock') return
    const version = requestVersion.current
    pendingRef.current = true
    setPending(true)
    try {
      const answer = await checkLearnAnswer(question.id, { selected_option: optionKey })
      if (version === requestVersion.current) {
        setSession((current) => current && ({
          ...current, feedback: { ...current.feedback, [question.id]: answer },
        }))
      }
    } catch (cause) {
      if (version === requestVersion.current) {
        setError(cause instanceof Error ? cause.message : 'Could not check this answer.')
      }
    } finally {
      if (version === requestVersion.current) {
        pendingRef.current = false
        setPending(false)
      }
    }
  }

  async function nextQuestion() {
    if (!session || pendingRef.current) return
    const question = session.questions[session.questionIndex]
    if (session.mode.kind === 'mock' ? !session.selectedOptions[question.id] : !session.feedback[question.id]) return
    setError(null)
    if (session.questionIndex < session.questions.length - 1) {
      setSession({ ...session, questionIndex: session.questionIndex + 1 })
      return
    }
    if (session.mode.kind !== 'mock') {
      setSession({ ...session, finished: true })
      return
    }
    const answers = getMockTestAnswers(session.questions, session.selectedOptions)
    if (!answers) return
    const version = requestVersion.current
    pendingRef.current = true
    setPending(true)
    try {
      const grade = await gradeMockTest({ answers })
      if (version === requestVersion.current) {
        setSession((current) => current && ({ ...current, grade, finished: true }))
      }
    } catch (cause) {
      if (version === requestVersion.current) {
        setError(cause instanceof Error ? cause.message : 'Could not grade this test. Please try again.')
      }
    } finally {
      if (version === requestVersion.current) {
        pendingRef.current = false
        setPending(false)
      }
    }
  }

  if (!session && loadMode) {
    return (
      <div className="learn-page">
        <button className="learn-back" type="button" aria-label="Back to Learn" onClick={backToLearn}>←</button>
        {loading ? <p role="status">Loading questions…</p> : (
          <>
            <p className="error-message" role="alert">{error}</p>
            <button className="button button-secondary" type="button" onClick={() => startPractice(loadMode)}>Retry</button>
          </>
        )}
      </div>
    )
  }

  if (!session) {
    return (
      <div className="learn-page learn-launcher">
        <div className="learn-mode-cards">
          <button ref={launcherButton} className="learn-mode-card learn-mock-card" type="button" onClick={() => startPractice({ kind: 'mock' })}>
            <svg className="learn-mode-icon" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M29 5H12a3 3 0 0 0-3 3v32a3 3 0 0 0 3 3h24a3 3 0 0 0 3-3V15L29 5Zm0 0v10h10M17 28l5 5 10-11" />
            </svg>
            <strong>Mock test</strong>
            <span className="learn-mode-meta">Practice test</span>
          </button>
          <button className="learn-mode-card learn-quick-card" type="button" onClick={() => startPractice({ kind: 'quick' })}>
            <svg className="learn-mode-icon" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="m27 4-17 23h12l-1 17 17-25H26l1-15Z" />
            </svg>
            <strong>Quick</strong>
            <span className="learn-mode-meta">3 Q</span>
          </button>
        </div>
        <section className="learn-topics" aria-labelledby="learn-topics-title">
          <h2 id="learn-topics-title">Topics</h2>
          {topicsError ? (
            <>
              <p className="error-message" role="alert">{topicsError}</p>
              <button className="button button-secondary" type="button" onClick={() => setTopicsAttempt((attempt) => attempt + 1)}>Retry</button>
            </>
          ) : topics === null ? <p role="status">Loading topics…</p>
            : topics.length === 0 ? <p role="status">No topics are currently available.</p>
              : (
                <div className="learn-topic-grid">
                  {topics.map((topic) => (
                    <button key={topic.id} className="learn-topic-card" type="button" onClick={() => startPractice({ kind: 'topic', topic })}>
                      <span aria-hidden="true">▤</span>
                      <div className="learn-topic-copy">
                        <strong>{topic.name}</strong>
                        {topic.description && <small>{topic.description}</small>}
                        {topic.trip_matchable && <small>Available for trip prep</small>}
                      </div>
                    </button>
                  ))}
                </div>
              )}
        </section>
      </div>
    )
  }

  if (session.finished) {
    const grade = session.grade
    const score = grade ? grade.score : Object.values(session.feedback).filter((answer) => answer.correct).length
    const total = grade ? grade.total : session.questions.length
    const percentage = grade ? grade.percentage : Math.round(score * 100 / total)
    const passed = grade ? grade.passed : score === total
    return (
      <div className="learn-page learn-result">
        <div className={`learn-score ${passed ? 'is-correct' : 'is-incorrect'}`} aria-label={`${score} of ${total} correct`}>
          <span>{percentage}%</span>
        </div>
        <h2 ref={questionHeading} tabIndex={-1}>{grade ? (grade.passed ? 'Pass' : 'Try again') : 'Practice complete'}</h2>
        <p>{score} of {total} correct{grade && <> · Pass mark {grade.pass_mark_percent}%</>}</p>
        <div className="learn-result-actions">
          <button className="button button-secondary" type="button" onClick={() => startPractice(session.mode)}>Again</button>
          <button className="button button-primary" type="button" onClick={backToLearn}>Done</button>
        </div>
        {grade && (
          <section className="learn-review" aria-labelledby="learn-review-title">
            <h3 id="learn-review-title">Question review</h3>
            {grade.results.map((result, index) => {
              const question = session.questions.find((item) => item.id === result.question_id)
              const selectedText = question?.options.find((option) => option.key === result.selected_option)?.text
              const correctText = question?.options.find((option) => option.key === result.correct_option)?.text
              return (
                <details key={result.question_id}>
                  <summary>
                    {index + 1}. {question?.prompt ?? result.question_id}
                    {' — '}{result.correct ? 'Correct' : 'Incorrect'}
                  </summary>
                  <p>Your answer: {selectedText ?? result.selected_option}</p>
                  <p>Correct answer: {correctText ?? result.correct_option}</p>
                  <p>{result.explanation}</p>
                  <LearnSourceReference source={result.source} />
                </details>
              )
            })}
          </section>
        )}
      </div>
    )
  }

  const question = session.questions[session.questionIndex]
  const answer = session.feedback[question.id]
  const selected = session.selectedOptions[question.id]
  const isMock = session.mode.kind === 'mock'
  const isLastQuestion = session.questionIndex === session.questions.length - 1
  const topicName = session.mode.kind === 'topic' ? session.mode.topic.name
    : topics?.find((topic) => topic.id === question.topic_id)?.name ?? question.topic_id.replaceAll('_', ' ')

  return (
    <div className="learn-page learn-quiz">
      <header className="learn-quiz-header">
        <button className="learn-back" type="button" aria-label="Back to Learn" onClick={backToLearn}>←</button>
        <progress className="learn-progress" value={session.questionIndex + 1} max={session.questions.length} aria-label="Quiz progress" />
        <span className="learn-counter">{session.questionIndex + 1} / {session.questions.length}</span>
      </header>
      {isMock && <p className="learn-mode-meta">{session.totalQuestions} questions · Pass mark {session.passMarkPercent}%</p>}
      <section className="learn-question" aria-labelledby="learn-question-title">
        <span className="learn-pill">{topicName}</span>
        <h2 id="learn-question-title" ref={questionHeading} tabIndex={-1}>{question.prompt}</h2>
        {question.scenario?.description && <p>{question.scenario.description}</p>}
        <div className="learn-options">
          {question.options.map((option) => {
            const correct = Boolean(answer && option.key === answer.correct_option)
            const incorrect = Boolean(answer && option.key === answer.selected_option && !answer.correct)
            return (
              <button key={option.key} className={`learn-option${correct ? ' correct' : incorrect ? ' incorrect' : selected === option.key ? ' selected' : ''}`}
                type="button" disabled={pending || Boolean(answer)}
                aria-pressed={isMock ? selected === option.key : undefined}
                onClick={() => chooseOption(option.key)}>
                <span>{option.text}</span>
                {(correct || incorrect) && <>
                  <span className="learn-answer-mark" aria-hidden="true">{correct ? '✓' : '×'}</span>
                  <span className="sr-only">{correct ? 'Correct answer' : 'Incorrect answer'}</span>
                </>}
              </button>
            )
          })}
        </div>
      </section>
      {answer && (
        <section className={`learn-feedback ${answer.correct ? 'is-correct' : 'is-incorrect'}`} aria-live="polite">
          <span className="learn-verdict-mark" role="img" aria-label={answer.correct ? 'Correct' : 'Incorrect'}>{answer.correct ? '✓' : '×'}</span>
          <p>{answer.explanation}</p>
          <LearnSourceReference source={answer.source} />
        </section>
      )}
      {pending && <p role="status">{isMock ? 'Grading test…' : 'Checking answer…'}</p>}
      {error && <p className="error-message" role="alert">{error}{!isMock && ' Select an option to retry.'}</p>}
      <div className="learn-navigation">
        {isMock && <button className="button button-secondary" type="button" disabled={session.questionIndex === 0 || pending}
          onClick={() => { setError(null); setSession({ ...session, questionIndex: session.questionIndex - 1 }) }}>Previous</button>}
        <button className="button button-primary learn-next" type="button" onClick={nextQuestion}
          disabled={pending || (isMock ? !selected || (isLastQuestion && !getMockTestAnswers(session.questions, session.selectedOptions)) : !answer)}>
          {isLastQuestion ? (isMock ? (error ? 'Retry grading' : 'Submit test') : 'Done') : 'Next →'}
        </button>
      </div>
    </div>
  )
}

function TripLearnPractice({
  tripLesson,
}: {
  tripLesson: TripLessonResponse
}) {
  const [practice, setPractice] = useState<TripPracticeState>({
    questionIndex: 0,
    answers: {},
    finished: false,
  })
  const [submitting, setSubmitting] = useState(false)
  const [answerError, setAnswerError] = useState<string | null>(null)
  const submittingRef = useRef(false)

  const questionHeading = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    questionHeading.current?.focus()
  }, [practice.questionIndex, practice.finished])

  const question = tripLesson.questions[practice.questionIndex]
  const answer = question
    ? practice.answers[question.id]
    : undefined

  async function chooseOption(optionKey: string) {
    if (!question || answer || submittingRef.current) return

    submittingRef.current = true
    setSubmitting(true)
    setAnswerError(null)

    try {
      const result = await checkLearnAnswer(
        question.id,
        {
          selected_option: optionKey,
        },
      )

      setPractice((current) => ({
        ...current,
        answers: {
          ...current.answers,
          [question.id]: {
            selectedOption: result.selected_option,
            correct: result.correct,
            correctOption: result.correct_option,
            explanation: result.explanation,
            sourceName: result.source.name,
            sourceUrl: result.source.url,
          },
        },
      }))
    } catch (error) {
      setAnswerError(error instanceof Error ? error.message : 'Could not check this answer. Please try again.')
    } finally {
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  function nextQuestion() {
    if (!question || !answer) return

    if (
      practice.questionIndex
      === tripLesson.questions.length - 1
    ) {
      setPractice((current) => ({
        ...current,
        finished: true,
      }))
      return
    }

    setPractice((current) => ({
      ...current,
      questionIndex: current.questionIndex + 1,
    }))
  }

  if (practice.finished) {
    const results = Object.values(practice.answers)
    const correctCount = results.filter(
      (result) => result.correct,
    ).length

    const percentage = Math.round(
      (correctCount / tripLesson.questions.length) * 100,
    )

    return (
      <div className="learn-page learn-result">
        <div
          className="learn-score is-correct"
          aria-label={`${correctCount} of ${tripLesson.questions.length} correct`}
        >
          <span>{percentage}%</span>
        </div>

        <h2 ref={questionHeading} tabIndex={-1}>
          Trip prep complete
        </h2>

        <p>
          {correctCount} of {tripLesson.questions.length} correct
        </p>

        <div className="learn-result-actions">
          <button
            className="button button-primary"
            type="button"
            onClick={() => {
              setPractice({
                questionIndex: 0,
                answers: {},
                finished: false,
              })
            }}
          >
            Again
          </button>
        </div>
      </div>
    )
  }

  if (!question) {
    return null
  }

  const topicLabel = question.topic_id
    .replaceAll('_', ' ')

  return (
    <div className="learn-page learn-quiz">
      <header className="learn-quiz-header">
        <progress
          className="learn-progress"
          value={practice.questionIndex + 1}
          max={tripLesson.questions.length}
          aria-label="Trip preparation progress"
        />

        <span className="learn-counter">
          {practice.questionIndex + 1}
          {' / '}
          {tripLesson.questions.length}
        </span>
      </header>

      <section
        className="learn-question"
        aria-labelledby="trip-learn-question-title"
      >
        <span className="learn-pill">
          {topicLabel}
        </span>

        <h2
          id="trip-learn-question-title"
          ref={questionHeading}
          tabIndex={-1}
        >
          {question.prompt}
        </h2>

        {question.scenario?.description && (
          <p>{question.scenario.description}</p>
        )}

        <div className="learn-options">
          {question.options.map((option) => {
            const correct = Boolean(
              answer
              && option.key === answer.correctOption,
            )

            const incorrect = Boolean(
              answer
              && option.key === answer.selectedOption
              && !answer.correct,
            )

            return (
              <button
                key={option.key}
                className={
                  `learn-option${
                    correct
                      ? ' correct'
                      : incorrect
                        ? ' incorrect'
                        : ''
                  }`
                }
                type="button"
                onClick={() => chooseOption(option.key)}
                disabled={Boolean(answer) || submitting}
              >
                <span>{option.text}</span>

                {(correct || incorrect) && (
                  <>
                    <span
                      className="learn-answer-mark"
                      aria-hidden="true"
                    >
                      {correct ? '✓' : '×'}
                    </span>

                    <span className="sr-only">
                      {correct
                        ? 'Correct answer'
                        : 'Incorrect answer'}
                    </span>
                  </>
                )}
              </button>
            )
          })}
        </div>
      </section>

      {answer && (
        <section
          className={
            `learn-feedback ${
              answer.correct
                ? 'is-correct'
                : 'is-incorrect'
            }`
          }
          aria-live="polite"
        >
          <span
            className="learn-verdict-mark"
            role="img"
            aria-label={
              answer.correct
                ? 'Correct'
                : 'Incorrect'
            }
          >
            {answer.correct ? '✓' : '×'}
          </span>

          <p>{answer.explanation}</p>

          <LearnSourceReference source={{ name: answer.sourceName, url: answer.sourceUrl }} />
        </section>
      )}

      {answerError && <p className="error-message" role="alert">{answerError} Select an option to retry.</p>}

      <button
        className="button button-primary learn-next"
        type="button"
        onClick={nextQuestion}
        disabled={!answer}
      >
        {practice.questionIndex
        === tripLesson.questions.length - 1
          ? 'Done'
          : 'Next →'}
      </button>
    </div>
  )
}


// Compatibility for older trip links that did not carry a backend trip lesson.
function LegacyTripPractice({ tripLessonIds }: { tripLessonIds: Lesson['id'][] }) {
  const [session, setSession] = useState<PracticeSession | null>(() => (
    tripLessonIds.length > 0 ? {
      lessons: tripLessonIds.flatMap((id) => LESSONS.filter((lesson) => lesson.id === id)),
      questionIndex: 0,
      answers: [],
      finished: false,
    } : null
  ))
  const questionHeading = useRef<HTMLHeadingElement>(null)
  const questionIndex = session?.questionIndex
  const finished = session?.finished

  useEffect(() => {
    if (questionIndex !== undefined) questionHeading.current?.focus()
  }, [questionIndex, finished])

  function startPractice() {
    const lessons = tripLessonIds.flatMap((id) => LESSONS.filter((lesson) => lesson.id === id))
    setSession({ lessons, questionIndex: 0, answers: [], finished: false })
  }

  function chooseOption(index: number) {
    setSession((current) => {
      if (!current || current.finished || current.answers.length > current.questionIndex) return current
      return { ...current, answers: [...current.answers, index] }
    })
  }

  function nextQuestion() {
    if (!session || session.answers.length <= session.questionIndex) return
    if (session.questionIndex === session.lessons.length - 1) {
      addCompletedTopics(session.lessons.slice(0, session.answers.length).map((lesson) => lesson.topic))
      setSession({ ...session, finished: true })
    } else {
      setSession({ ...session, questionIndex: session.questionIndex + 1 })
    }
  }

  if (!session) {
    return <LearnBankPractice />
  }

  if (session.finished) {
    const correctCount = session.answers.filter((answer, index) => answer === session.lessons[index].answerIndex).length
    const percentage = Math.round((correctCount / session.lessons.length) * 100)
    const passed = correctCount === session.lessons.length

    return (
      <div className="learn-page learn-result">
        <div className={`learn-score ${passed ? 'is-correct' : 'is-incorrect'}`} aria-label={`${correctCount} of ${session.lessons.length} correct`}>
          <span>{percentage}%</span>
        </div>
        <h2 ref={questionHeading} tabIndex={-1}><span aria-hidden="true">{passed ? '✓' : '×'}</span> {passed ? 'Pass' : 'Try again'}</h2>
        <div className="learn-result-actions">
          <button className="button button-secondary" type="button" onClick={startPractice}>Again</button>
          <button className="button button-primary" type="button" onClick={() => setSession(null)}>Done</button>
        </div>
      </div>
    )
  }

  const lesson = session.lessons[session.questionIndex]
  const answered = session.answers[session.questionIndex] ?? null
  const feedback = getLessonFeedback(lesson, answered)
  const isCorrect = feedback?.isCorrect ?? false
  const isLastQuestion = session.questionIndex === session.lessons.length - 1

  return (
    <div className="learn-page learn-quiz">
      <header className="learn-quiz-header">
        <button className="learn-back" type="button" aria-label="Back to Learn" onClick={() => setSession(null)}>←</button>
        <progress className="learn-progress" value={session.questionIndex + 1} max={session.lessons.length} aria-label="Quiz progress" />
        <span className="learn-counter">{session.questionIndex + 1} / {session.lessons.length}</span>
      </header>

      <section className="learn-question" aria-labelledby="learn-question-title">
        <span className="learn-pill"><span aria-hidden="true">{lesson.icon}</span> {lesson.shortLabel}</span>
        <h2 id="learn-question-title" ref={questionHeading} tabIndex={-1}>{lesson.question}</h2>
        <div className="learn-options">
          {lesson.options.map((option, index) => {
            const correct = answered !== null && index === lesson.answerIndex
            const incorrect = answered !== null && index === answered && !correct
            return (
              <button
                key={option}
                className={`learn-option${correct ? ' correct' : incorrect ? ' incorrect' : ''}`}
                type="button"
                onClick={() => chooseOption(index)}
                disabled={answered !== null}
              >
                <span>{option}</span>
                {(correct || incorrect) && (
                  <>
                    <span className="learn-answer-mark" aria-hidden="true">{correct ? '✓' : '×'}</span>
                    <span className="sr-only">{correct ? 'Correct answer' : 'Incorrect answer'}</span>
                  </>
                )}
              </button>
            )
          })}
        </div>
      </section>

      {feedback !== null && (
        <section className={`learn-feedback ${isCorrect ? 'is-correct' : 'is-incorrect'}`} aria-live="polite">
          <span className="learn-verdict-mark" role="img" aria-label={isCorrect ? 'Correct' : 'Incorrect'}>{isCorrect ? '✓' : '×'}</span>
          <p>{feedback.explanation}</p>
          <a className="learn-source" href={lesson.source.href} target="_blank" rel="noreferrer"><span aria-hidden="true">↗</span> {lesson.source.name}</a>
        </section>
      )}

      <button className="button button-primary learn-next" type="button" onClick={nextQuestion} disabled={answered === null}>
        {isLastQuestion ? 'Done' : 'Next →'}
      </button>
    </div>
  )
}

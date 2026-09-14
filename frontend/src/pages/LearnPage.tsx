import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { addCompletedTopics, getLessonFeedback, getTripLessonIds, LESSONS } from '../data/lessons'
import type { Lesson } from '../data/lessons'
import { useTripResult } from '../state/tripResult'
import './LearnPage.css'

type PracticeMode =
  | { kind: 'mock' }
  | { kind: 'quick' }
  | { kind: 'topic'; topicId: Lesson['id'] }
  | { kind: 'trip'; lessonIds: Lesson['id'][] }

type PracticeSession = {
  mode: PracticeMode
  lessons: Lesson[]
  questionIndex: number
  answers: number[]
  finished: boolean
}

const MOCK_PASS_MARK = 78

function shuffledLessons(): Lesson[] {
  const lessons = [...LESSONS]
  for (let index = lessons.length - 1; index > 0; index -= 1) {
    const otherIndex = Math.floor(Math.random() * (index + 1))
    ;[lessons[index], lessons[otherIndex]] = [lessons[otherIndex], lessons[index]]
  }
  return lessons
}

export default function LearnPage() {
  const [searchParams] = useSearchParams()
  const [tripResult] = useTripResult()
  const tripLessonIds = searchParams.get('mode') === 'trip' && tripResult
    ? getTripLessonIds(tripResult.factors)
    : []

  // Reset on a different trip match or a return to /learn, without a landing
  // screen flash before trip practice. This remains the same quiz UI.
  return <LearnPractice key={tripLessonIds.join(',') || 'practice'} tripLessonIds={tripLessonIds} />
}

function LearnPractice({ tripLessonIds }: { tripLessonIds: Lesson['id'][] }) {
  const [session, setSession] = useState<PracticeSession | null>(() => (
    tripLessonIds.length > 0 ? {
      mode: { kind: 'trip', lessonIds: tripLessonIds },
      lessons: tripLessonIds.flatMap((id) => LESSONS.filter((lesson) => lesson.id === id)),
      questionIndex: 0,
      answers: [],
      finished: false,
    } : null
  ))
  const questionHeading = useRef<HTMLHeadingElement>(null)
  const launcherButton = useRef<HTMLButtonElement>(null)
  const questionIndex = session?.questionIndex
  const finished = session?.finished

  useEffect(() => {
    if (questionIndex !== undefined) questionHeading.current?.focus()
    else launcherButton.current?.focus()
  }, [questionIndex, finished])

  function startPractice(mode: PracticeMode) {
    const lessons = mode.kind === 'trip'
      ? mode.lessonIds.flatMap((id) => LESSONS.filter((lesson) => lesson.id === id))
      : mode.kind === 'topic'
        ? LESSONS.filter((lesson) => lesson.id === mode.topicId)
        : shuffledLessons().slice(0, mode.kind === 'quick' ? 3 : 4)

    setSession({ mode, lessons, questionIndex: 0, answers: [], finished: false })
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
    return (
      <div className="learn-page learn-launcher">
        <div className="learn-mode-cards">
          <button
            ref={launcherButton}
            className="learn-mode-card learn-mock-card"
            type="button"
            onClick={() => startPractice({ kind: 'mock' })}
          >
            <svg className="learn-mode-icon" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M29 5H12a3 3 0 0 0-3 3v32a3 3 0 0 0 3 3h24a3 3 0 0 0 3-3V15L29 5Zm0 0v10h10M17 28l5 5 10-11" />
            </svg>
            <strong>Mock test</strong>
            <span className="learn-mode-meta"><span>4 Q</span><span aria-label="Pass mark 78%">78%</span></span>
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
          <div className="learn-topic-grid">
            {LESSONS.map((lesson) => (
              <button key={lesson.id} className="learn-topic-card" type="button" aria-label={lesson.topic} onClick={() => startPractice({ kind: 'topic', topicId: lesson.id })}>
                <span aria-hidden="true">{lesson.icon}</span>
                <strong>{lesson.shortLabel}</strong>
              </button>
            ))}
          </div>
        </section>
      </div>
    )
  }

  if (session.finished) {
    const correctCount = session.answers.filter((answer, index) => answer === session.lessons[index].answerIndex).length
    const percentage = Math.round((correctCount / session.lessons.length) * 100)
    const passed = session.mode.kind === 'mock'
      ? percentage >= MOCK_PASS_MARK
      : correctCount === session.lessons.length

    return (
      <div className="learn-page learn-result">
        <div className={`learn-score ${passed ? 'is-correct' : 'is-incorrect'}`} aria-label={`${correctCount} of ${session.lessons.length} correct`}>
          <span>{percentage}%</span>
        </div>
        <h2 ref={questionHeading} tabIndex={-1}><span aria-hidden="true">{passed ? '✓' : '×'}</span> {passed ? 'Pass' : 'Try again'}</h2>
        <div className="learn-result-actions">
          <button className="button button-secondary" type="button" onClick={() => startPractice(session.mode)}>Again</button>
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

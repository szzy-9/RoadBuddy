import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getLessonFeedback } from '../src/data/lessons.ts'
import type { Lesson } from '../src/data/lessons.ts'

const lesson: Lesson = {
  id: 'night',
  topic: 'Night driving',
  shortLabel: 'Night',
  icon: '☾',
  question: 'Example question',
  options: ['Correct', 'Wrong', 'Also wrong'],
  answerIndex: 0,
  why: 'This is the short explanation.',
  source: {
    name: 'Road to Solo Driving',
    href: 'https://example.com',
  },
}

test('lesson feedback is absent before an answer is submitted', () => {
  assert.equal(getLessonFeedback(lesson, null), null)
})

test('correct answer feedback includes the lesson explanation', () => {
  assert.deepEqual(getLessonFeedback(lesson, 0), {
    isCorrect: true,
    explanation: 'This is the short explanation.',
  })
})

test('incorrect answer feedback still includes the lesson explanation', () => {
  assert.deepEqual(getLessonFeedback(lesson, 1), {
    isCorrect: false,
    explanation: 'This is the short explanation.',
  })
})

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getMockTestAnswers } from '../src/lib/learnPractice.ts'

const questions = [{ id: 'q2' }, { id: 'q1' }]

test('mock submission waits until every question has an answer', () => {
  assert.equal(getMockTestAnswers(questions, { q2: 'B' }), null)
})

test('mock submission includes only the current questions in their original order', () => {
  assert.deepEqual(getMockTestAnswers(questions, { q1: 'D', old: 'A', q2: 'B' }), [
    { question_id: 'q2', selected_option: 'B' },
    { question_id: 'q1', selected_option: 'D' },
  ])
})

test('an empty mock test cannot be submitted for grading', () => {
  assert.equal(getMockTestAnswers([], {}), null)
})

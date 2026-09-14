import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getTripLessonIds } from '../src/data/lessons'
import type { RiskFactor } from '../src/types/api'

test('after_dark matches the night lesson', () => {
  const factor: RiskFactor = { type: 'after_dark', label: 'After dark' }
  assert.deepEqual(getTripLessonIds([factor]), ['night'])
})

test('rain matches the wet lesson', () => {
  const factor: RiskFactor = { type: 'rain', label: 'Rain' }
  assert.deepEqual(getTripLessonIds([factor]), ['wet'])
})

test('high_speed_zone matches the high_speed lesson', () => {
  const factor: RiskFactor = { type: 'high_speed_zone', label: 'High-speed zone' }
  assert.deepEqual(getTripLessonIds([factor]), ['high_speed'])
})

test('significant_crash_history matches the crash_history lesson', () => {
  const factor: RiskFactor = { type: 'significant_crash_history', label: 'Crash history' }
  assert.deepEqual(getTripLessonIds([factor]), ['crash_history'])
})

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

test('multiple trip conditions select only their matching lessons', () => {
  const afterDark: RiskFactor = { type: 'after_dark', label: 'After dark' }
  const highSpeed: RiskFactor = { type: 'high_speed_zone', label: 'High-speed zone' }

  assert.deepEqual(getTripLessonIds([afterDark, highSpeed]), ['night', 'high_speed'])
})

test('trip lesson matching is deterministic when factor input order changes', () => {
  const crashHistory: RiskFactor = { type: 'significant_crash_history', label: 'Crash history' }
  const rain: RiskFactor = { type: 'rain', label: 'Rain' }
  const afterDark: RiskFactor = { type: 'after_dark', label: 'After dark' }

  assert.deepEqual(getTripLessonIds([crashHistory, rain, afterDark]), [
    'night', 'wet', 'crash_history',
  ])
  assert.deepEqual(getTripLessonIds([afterDark, crashHistory, rain]), [
    'night', 'wet', 'crash_history',
  ])
})

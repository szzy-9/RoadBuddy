import assert from 'node:assert/strict'
import { test } from 'node:test'
import { bandColor, crashBand } from '../src/lib/crashBands.ts'

test('Radar and trip routes use the same exposure thresholds, including unavailable data', () => {
  const cases = [
    [0, 'green', '#2E9E5B'], [4, 'green', '#2E9E5B'],
    [5, 'yellow', '#E5B917'], [9, 'yellow', '#E5B917'],
    [10, 'orange', '#E8843C'], [19, 'orange', '#E8843C'],
    [20, 'red', '#D6453D'], [49, 'red', '#D6453D'],
    [50, 'purple', '#A63BC4'], [100, 'purple', '#A63BC4'],
    [null, 'unavailable', '#8A9496'],
  ] as const
  for (const [count, band, color] of cases) {
    assert.equal(crashBand(count).band, band)
    assert.equal(bandColor(count), color)
  }
})

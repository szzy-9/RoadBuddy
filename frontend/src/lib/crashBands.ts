/** Fixed historical crash-count bands shared by Risk Radar and trip sections. */
export const CRASH_COUNT_BANDS = [
  { min: 0, band: 'green', name: 'Green', color: '#2E9E5B', label: '0–4' },
  { min: 5, band: 'yellow', name: 'Yellow', color: '#E5B917', label: '5–9' },
  { min: 10, band: 'orange', name: 'Orange', color: '#E8843C', label: '10–19' },
  { min: 20, band: 'red', name: 'Red', color: '#D6453D', label: '20–49' },
  { min: 50, band: 'purple', name: 'Purple', color: '#A63BC4', label: '50+' },
] as const

export const UNAVAILABLE_CRASH_BAND = {
  band: 'unavailable', name: 'Grey', color: '#8A9496', label: 'Data unavailable',
} as const

export function crashBand(count: number | null) {
  if (count === null || !Number.isFinite(count) || count < 0) return UNAVAILABLE_CRASH_BAND
  return [...CRASH_COUNT_BANDS].reverse().find((band) => count >= band.min)!
}

export function bandColor(count: number | null): string {
  return crashBand(count).color
}

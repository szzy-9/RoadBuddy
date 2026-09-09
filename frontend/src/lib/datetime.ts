/**
 * Departure time helpers shared by every trip entry form.
 *
 * The form works in the browser's local time, because that is the time the
 * driver is thinking in, while the API needs an explicit offset so the same
 * instant is unambiguous on the server.
 */

/**
 * The current local time, formatted for a `datetime-local` input.
 *
 * @returns A `YYYY-MM-DDTHH:mm` string in the browser's timezone.
 */
export function localDateTimeDefault(): string {
  const date = new Date(Date.now())
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

/**
 * Attach the browser's UTC offset to a `datetime-local` value.
 *
 * @param localValue - A `YYYY-MM-DDTHH:mm` string from a datetime-local input.
 * @returns An ISO 8601 string with offset, or an empty string when the input is unparseable.
 */
export function withLocalOffset(localValue: string): string {
  const date = new Date(localValue)
  if (Number.isNaN(date.getTime())) return ''
  const offsetMinutes = -date.getTimezoneOffset()
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const absolute = Math.abs(offsetMinutes)
  const hours = String(Math.floor(absolute / 60)).padStart(2, '0')
  const minutes = String(absolute % 60).padStart(2, '0')
  return `${localValue}:00${sign}${hours}:${minutes}`
}

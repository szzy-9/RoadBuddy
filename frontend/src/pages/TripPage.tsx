import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { checkTrip } from '../api/client'
import AddressAutocomplete from '../components/AddressAutocomplete'
import LoadingState from '../components/LoadingState'
import { saveTripResult } from '../state/tripResult'

function localDateTimeDefault(): string {
  const date = new Date(Date.now())
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function withLocalOffset(localValue: string): string {
  const date = new Date(localValue)
  if (Number.isNaN(date.getTime())) return ''
  const offsetMinutes = -date.getTimezoneOffset()
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const absolute = Math.abs(offsetMinutes)
  const hours = String(Math.floor(absolute / 60)).padStart(2, '0')
  const minutes = String(absolute % 60).padStart(2, '0')
  return `${localValue}:00${sign}${hours}:${minutes}`
}

export default function TripPage() {
  const navigate = useNavigate()
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [departureTime, setDepartureTime] = useState(localDateTimeDefault)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (!origin.trim()) {
      setError('Enter where you are leaving from.')
      return
    }
    if (!destination.trim()) {
      setError('Enter where you are going.')
      return
    }
    const formattedDeparture = withLocalOffset(departureTime)
    if (!formattedDeparture) {
      setError('Choose a valid departure date and time.')
      return
    }

    setIsLoading(true)
    try {
      const response = await checkTrip({
        origin: origin.trim(),
        destination: destination.trim(),
        departure_time: formattedDeparture,
      })
      saveTripResult(response)
      navigate('/trip/result')
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Something went wrong. Please try again.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="trip-page page-wrap">
      <section className="page-heading">
        {/* <p className="eyebrow">Pre-journey risk check</p> */}
        {/* <p className="eyebrow">Check the road ahead</p> */}
        {/* <p className="lead">See the conditions that may deserve more care before you leave.</p> */}
      </section>

      {isLoading ? (
        <section className="trip-loading-screen" aria-live="polite">
          <LoadingState message="Checking route, weather and historical conditions…" />
        </section>
      ) : (
        <form className="trip-form" onSubmit={handleSubmit} noValidate>
          <div className="journey-fields">
            <AddressAutocomplete
              label="From address"
              value={origin}
              onChange={setOrigin}
              placeholder="e.g. Tarneit VIC 3029"
            />
            <span className="journey-arrow" aria-hidden="true">→</span>
            <AddressAutocomplete
              label="To address"
              value={destination}
              onChange={setDestination}
              placeholder="e.g. Docklands VIC 3008"
            />
          </div>
          <label className="departure-field">
            <span>Departure date and time</span>
            <input
              type="datetime-local"
              value={departureTime}
              onChange={(event) => setDepartureTime(event.target.value)}
            />
          </label>
          {error ? (
            <p className="trip-form-error" role="alert">{error}</p>
          ) : (
            <p className="form-privacy">
              Addresses are used for this check only and are not stored.
            </p>
          )}
          <button className="button button-primary submit-button" type="submit">
            Check this trip
          </button>
        </form>
      )}
    </div>
  )
}

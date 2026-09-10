import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { checkTrip } from '../api/client'
import { reverseGeocode } from '../api/reverseGeocode'
import AddressAutocomplete from '../components/AddressAutocomplete'
import { localDateTimeDefault, withLocalOffset } from '../lib/datetime'
import { saveTripResult } from '../state/tripResult'
import './TripSearchForm.css'

/**
 * The trip used by "load an example trip".
 *
 * A cross-town run from the outer west to the CBD, which is long enough to pass
 * through several speed zones and pick up real crash history, so the example
 * result shows the screen doing something rather than an empty one.
 */
const EXAMPLE_TRIP = {
  origin: 'Tarneit VIC 3029',
  destination: 'Docklands VIC 3008',
}

const GEOLOCATION_TIMEOUT_MS = 10_000

interface TripSearchFormProps {
  /** Heading above the form. Omitted on screens that already have one. */
  title?: string
  /** Supporting line under the heading. */
  subtitle?: string
  /** Text on the submit button. */
  submitLabel?: string
  /** Offer "load an example trip". Only worth showing where a user starts cold. */
  showExample?: boolean
  /**
   * Prefill the fields, for the result screen's "change this trip" form.
   *
   * Both addresses are treated as already resolved, so a prefilled form does
   * not fire a lookup and drop a dropdown over the card on mount.
   */
  initialOrigin?: string
  initialDestination?: string
  /** Supporting line under the submit button, in place of the privacy note. */
  footnote?: string
  /**
   * Told when a check starts and finishes.
   *
   * Lets the surrounding screen show the pending state where the result will
   * appear, rather than the form replacing itself and leaving the result area
   * looking untouched.
   */
  onLoadingChange?: (isLoading: boolean) => void
}

/**
 * Read the browser's current position.
 *
 * Wrapped as a promise so the caller can await it inside an async handler.
 * Geolocation is only available on secure origins, so this rejects on plain
 * HTTP as well as on refusal.
 *
 * @returns The current coordinates.
 */
function currentPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject(new Error('unsupported'))
      return
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: GEOLOCATION_TIMEOUT_MS,
      maximumAge: 60_000,
    })
  })
}

/**
 * The trip entry form, shared by the home screen and the trip screen.
 *
 * Both screens submit the same way, so the request, validation and navigation
 * live here rather than being duplicated per screen and drifting apart.
 *
 * @returns The form, or the loading screen while a check is in flight.
 */
export default function TripSearchForm({
  title,
  subtitle,
  submitLabel = 'Check my trip',
  showExample = false,
  initialOrigin = '',
  initialDestination = '',
  // footnote,
  onLoadingChange,
}: TripSearchFormProps) {
  const navigate = useNavigate()
  const [origin, setOrigin] = useState(initialOrigin)
  const [destination, setDestination] = useState(initialDestination)
  const [departureTime, setDepartureTime] = useState(localDateTimeDefault)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isLocating, setIsLocating] = useState(false)
  // Suppresses the autocomplete lookup that a programmatically filled field
  // would otherwise fire, which would drop a dropdown over the form.
  const [originIsResolved, setOriginIsResolved] = useState(Boolean(initialOrigin))
  const [destinationIsResolved, setDestinationIsResolved] = useState(
    Boolean(initialDestination),
  )

  async function handleUseLocation() {
    setError(null)
    setIsLocating(true)
    try {
      const position = await currentPosition()
      const { longitude, latitude } = position.coords
      const label = await reverseGeocode(longitude, latitude)
      if (!label) {
        setError('Could not work out an address for your location. Type it instead.')
        return
      }
      setOriginIsResolved(true)
      setOrigin(label)
    } catch {
      // Refusal, timeout and an insecure origin all land here; the user can
      // always type an address, so this stays a note rather than a blocker.
      setError('Location is unavailable. Check browser permissions, or type an address.')
    } finally {
      setIsLocating(false)
    }
  }

  function loadExample() {
    setError(null)
    setOriginIsResolved(true)
    setDestinationIsResolved(true)
    setOrigin(EXAMPLE_TRIP.origin)
    setDestination(EXAMPLE_TRIP.destination)
    setDepartureTime(localDateTimeDefault())
  }

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
    onLoadingChange?.(true)
    try {
      const response = await checkTrip({
        origin: origin.trim(),
        destination: destination.trim(),
        departure_time: formattedDeparture,
      })
      saveTripResult(response)
      navigate('/trip')
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Something went wrong. Please try again.',
      )
    } finally {
      setIsLoading(false)
      onLoadingChange?.(false)
    }
  }

  return (
    <form className="card trip-search-form" data-buddy-target="trip-form" onSubmit={handleSubmit} noValidate>
      {title && <h2 className="trip-search-title">{title}</h2>}
      {subtitle && <p className="trip-search-sub">{subtitle}</p>}

      <div className="field">
        <div className="field-row">
          <span className="field-row-label">From</span>
          <button
            className="text-button"
            type="button"
            onClick={handleUseLocation}
            disabled={isLocating}
          >
            <span aria-hidden="true">⌖</span>
            {isLocating ? 'Locating…' : 'Use my location'}
          </button>
        </div>
        <AddressAutocomplete
          label="From address"
          hideLabel
          value={origin}
          onChange={(value) => {
            setOriginIsResolved(false)
            setOrigin(value)
          }}
          valueIsResolved={originIsResolved}
          placeholder="Suburb or address"
        />
      </div>

      <div className="field">
        <span className="field-row-label">To</span>
        <AddressAutocomplete
          label="To address"
          hideLabel
          value={destination}
          onChange={(value) => {
            setDestinationIsResolved(false)
            setDestination(value)
          }}
          valueIsResolved={destinationIsResolved}
          placeholder="Suburb or address"
        />
      </div>

      <div className="field">
        <label className="field-row-label" htmlFor="departure-time">Leaving</label>
        <input
          id="departure-time"
          type="datetime-local"
          value={departureTime}
          onChange={(event) => setDepartureTime(event.target.value)}
        />
      </div>

      {error ? (
        <p className="trip-form-error" role="alert">{error}</p>
      ) 
      : ""
      // (
      //   <p className="form-privacy">
      //     {footnote ?? 'Addresses are used for this check only and are not stored.'}
      //   </p>
      // )
      }

      <button
        className="button button-primary submit-button"
        type="submit"
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <span className="button-spinner" aria-hidden="true" />
            Checking…
          </>
        ) : (
          <>
            {submitLabel} <span aria-hidden="true">→</span>
          </>
        )}
      </button>

      {showExample && (
        <p className="example-note">
          {/* <strong>Nothing entered yet?</strong>{' '} */}
          <button className="text-button inline" type="button" onClick={loadExample}>
            Load an example trip
          </button>{' '}
          to see how a result looks
        </p>
      )}
    </form>
  )
}

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ''
const REVERSE_GEOCODE_URL = 'https://api.mapbox.com/search/geocode/v6/reverse'
const REQUEST_TIMEOUT_MS = 8000

/**
 * Cache of resolved place names, keyed by rounded coordinate.
 *
 * Hotspot coordinates are stable for a given cluster, so the same trip checked
 * twice, or a sheet reopened, costs no further requests. The cache lives for
 * the page session only.
 */
const cache = new Map<string, string | null>()

/**
 * Build the cache key for a coordinate.
 *
 * Five decimal places is about a metre, far finer than a 200 m cluster, so
 * distinct hotspots never collide.
 *
 * @param longitude - Longitude in decimal degrees.
 * @param latitude - Latitude in decimal degrees.
 * @returns A stable cache key.
 */
function cacheKey(longitude: number, latitude: number): string {
  return `${longitude.toFixed(5)},${latitude.toFixed(5)}`
}

interface GeocodeContextEntry {
  name?: string
}

interface GeocodeFeature {
  properties?: {
    name?: string
    context?: {
      street?: GeocodeContextEntry
      locality?: GeocodeContextEntry
      place?: GeocodeContextEntry
      neighborhood?: GeocodeContextEntry
    }
  }
}

/**
 * Reduce a geocoder feature to a short "street, suburb" label.
 *
 * Only the street and the surrounding suburb are used. House numbers are
 * deliberately excluded: a crash cluster covers a 200 m grid square, so a
 * specific street address would imply more precision than the data carries.
 *
 * @param feature - A Mapbox geocoding feature.
 * @returns A display label, or null when the feature names no street or suburb.
 */
function labelFromFeature(feature: GeocodeFeature | undefined): string | null {
  const context = feature?.properties?.context
  if (!context) return null

  const street = context.street?.name ?? feature?.properties?.name ?? null
  const area =
    context.locality?.name
    ?? context.neighborhood?.name
    ?? context.place?.name
    ?? null

  if (street && area) return `${street}, ${area}`
  return street ?? area
}

/**
 * Look up a short place name for one coordinate.
 *
 * Failures resolve to null rather than throwing: a missing name degrades the
 * hotspot list to its crash counts, which is still correct, whereas a rejected
 * promise would take out the whole sheet.
 *
 * @param longitude - Longitude in decimal degrees.
 * @param latitude - Latitude in decimal degrees.
 * @param signal - Aborts the request when the caller unmounts.
 * @returns The place name, or null when unavailable.
 */
export async function reverseGeocode(
  longitude: number,
  latitude: number,
  signal?: AbortSignal,
): Promise<string | null> {
  if (!MAPBOX_TOKEN) return null

  const key = cacheKey(longitude, latitude)
  const cached = cache.get(key)
  if (cached !== undefined) return cached

  const controller = new AbortController()
  const onAbort = () => controller.abort()
  signal?.addEventListener('abort', onAbort, { once: true })
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const url =
      `${REVERSE_GEOCODE_URL}?longitude=${longitude}&latitude=${latitude}`
      + `&types=street&limit=1&access_token=${MAPBOX_TOKEN}`
    const response = await fetch(url, { signal: controller.signal })
    if (!response.ok) return null

    const body = await response.json() as { features?: GeocodeFeature[] }
    const label = labelFromFeature(body.features?.[0])
    // Cache negatives too, so a coordinate the geocoder cannot name is not
    // retried on every reopen of the sheet.
    cache.set(key, label)
    return label
  } catch {
    // Aborted, offline, or malformed: no name, no error surfaced.
    return null
  } finally {
    window.clearTimeout(timeoutId)
    signal?.removeEventListener('abort', onAbort)
  }
}

/**
 * Look up place names for several coordinates at once.
 *
 * Requests run in parallel; the geocoder has no batch reverse endpoint, and a
 * trip returns at most a handful of hotspots.
 *
 * @param points - Coordinates to name.
 * @param signal - Aborts all requests when the caller unmounts.
 * @returns Labels in the same order as `points`, null where unavailable.
 */
export async function reverseGeocodeAll(
  points: Array<{ longitude: number; latitude: number }>,
  signal?: AbortSignal,
): Promise<Array<string | null>> {
  return Promise.all(
    points.map((point) => reverseGeocode(point.longitude, point.latitude, signal)),
  )
}

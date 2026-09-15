import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import LoadingState from '../components/LoadingState'
import TripSearchForm from '../components/TripSearchForm'
import TripRouteMap from '../components/TripRouteMap'
import { reverseGeocodeAll } from '../api/reverseGeocode'
import { useTripResult } from '../state/tripResult'
import { getTripLesson } from '../api/client'
import type {
  ConcernLevel,
  DepartureComparisonOption,
  RiskFactor,
  TripCheckResponse,
  TripHotspot,
} from '../types/api'


/**
 * Format a timestamp as 24-hour clock time for the comparison cards.
 *
 * @param value - An ISO 8601 timestamp.
 * @returns A zero-padded "HH:mm" string.
 */
function formatComparisonTime(value: string): string {
  return new Intl.DateTimeFormat('en-AU', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

/**
 * Great-circle distance between two points, in kilometres.
 *
 * @param aLongitude - First point longitude in decimal degrees.
 * @param aLatitude - First point latitude in decimal degrees.
 * @param bLongitude - Second point longitude in decimal degrees.
 * @param bLatitude - Second point latitude in decimal degrees.
 * @returns The distance in kilometres.
 */
function distanceKm(
  aLongitude: number,
  aLatitude: number,
  bLongitude: number,
  bLatitude: number,
): number {
  const EARTH_RADIUS_KM = 6371
  const toRadians = (degrees: number) => (degrees * Math.PI) / 180
  const deltaLat = toRadians(bLatitude - aLatitude)
  const deltaLon = toRadians(bLongitude - aLongitude)
  const a =
    Math.sin(deltaLat / 2) ** 2
    + Math.cos(toRadians(aLatitude)) * Math.cos(toRadians(bLatitude)) * Math.sin(deltaLon / 2) ** 2
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(a))
}


/**
 * Describe where a hotspot sits relative to the trip's two endpoints.
 *
 * The backend returns coordinates but no place name, so the label is built
 * from the endpoints the user themselves typed rather than inventing a suburb
 * or street the response does not contain. Returns null when the backend omits
 * endpoint coordinates, in which case no location claim is made at all.
 *
 * @param hotspot - The hotspot to describe.
 * @param route - The route summary carrying the endpoint labels and points.
 * @returns A short phrase such as "1.2 km from Footscray VIC 3011", or null.
 */
function hotspotLocationLabel(
  hotspot: TripHotspot,
  route: TripCheckResponse['route'],
): string | null {
  const origin = route.origin_point
  const destination = route.destination_point
  if (!origin || !destination) return null

  const toOrigin = distanceKm(
    hotspot.longitude,
    hotspot.latitude,
    origin.longitude,
    origin.latitude,
  )
  const toDestination = distanceKm(
    hotspot.longitude,
    hotspot.latitude,
    destination.longitude,
    destination.latitude,
  )
  const nearestIsOrigin = toOrigin <= toDestination
  const distance = nearestIsOrigin ? toOrigin : toDestination
  const label = nearestIsOrigin ? route.origin : route.destination
  const rounded = distance < 10 ? distance.toFixed(1) : Math.round(distance).toString()
  return `${rounded} km from ${label}`
}

/**
 * Build the notice shown when one or more upstream data sources were missing.
 *
 * Wording stays explicit that nothing has been inferred from absent data.
 *
 * @param dataStatus - Per-source availability from the trip check.
 * @returns A sentence naming the unavailable sources, or null when all present.
 */
function partialDataMessage(dataStatus: TripCheckResponse['data_status']): string | null {
  // Weather is not part of this iteration's result at all, so its absence is
  // not a gap worth reporting; mentioning it would point at something the
  // screen never promised to show.
  const weatherUnavailable = false
  const crashUnavailable = dataStatus.crash_data === 'unavailable'
  const speedZonesUnavailable = dataStatus.speed_zones === 'unavailable'
  const unavailableCount = [
    weatherUnavailable,
    crashUnavailable,
    speedZonesUnavailable,
  ].filter(Boolean).length

  if (unavailableCount === 0) return null
  if (unavailableCount === 1) {
    if (weatherUnavailable) {
      return 'Weather data is unavailable. This check uses the other available information.'
    }
    if (crashUnavailable) {
      return 'Crash history is unavailable. No crash information has been inferred.'
    }
    return 'Speed-zone data is unavailable. This check does not include speed-zone context.'
  }

  const unavailableSources = [
    weatherUnavailable ? 'weather data' : null,
    crashUnavailable ? 'crash history' : null,
    speedZonesUnavailable ? 'speed-zone data' : null,
  ].filter((source): source is string => source !== null)
  const sourceSummary = unavailableSources.length === 2
    ? unavailableSources.join(' and ')
    : `${unavailableSources.slice(0, -1).join(', ')} and ${unavailableSources.at(-1)}`
  const capitalizedSourceSummary = sourceSummary[0].toUpperCase() + sourceSummary.slice(1)
  const limitations = [
    crashUnavailable ? 'no crash information has been inferred' : null,
    speedZonesUnavailable ? 'speed-zone context is not included' : null,
  ].filter((limitation): limitation is string => limitation !== null)
  const limitationSummary = limitations.length > 0
    ? `; ${limitations.join(' and ')}`
    : ''

  return `${capitalizedSourceSummary} are unavailable. This check uses the remaining available information${limitationSummary}.`
}

/** Terse forms of each factor, for the line under a concern badge. */
const SHORT_FACTOR_LABELS: Record<RiskFactor['type'], string> = {
  rain: 'rain',
  after_dark: 'after dark',
  high_speed_zone: 'high-speed road',
  significant_crash_history: 'crash history',
}

/** The single word shown on a concern badge. */
const CONCERN_WORDS: Record<ConcernLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  higher: 'High',
}

/** The headline that opens the result, in the user's own terms. */
const CONCERN_HEADLINES: Record<ConcernLevel, string> = {
  low: 'About as usual for this route',
  medium: 'A little more demanding than usual',
  higher: 'More demanding than usual',
}

/**
 * The full concern scale, always shown in order.
 *
 * Every level is listed rather than only the one that applies, so a driver can
 * see where this trip sits relative to the others instead of reading a bare
 * label with nothing to compare it against.
 */
const CONCERN_SCALE: Array<{ level: ConcernLevel; title: string; detail: string }> = [
  {
    level: 'low',
    title: 'Nothing unusual about this one',
    detail: 'Conditions on this route at this hour look like an ordinary drive.',
  },
  {
    level: 'medium',
    title: 'One or two things worth adjusting for',
    detail: 'Leave more gap, slow earlier, and check whether a later departure removes one of the factors.',
  },
  {
    level: 'higher',
    title: 'Several factors are stacking up',
    detail: 'The drive asks more of you than usual. Consider waiting if the comparison below shows it helps.',
  },
]

/**
 * How many crash clusters the result lists.
 *
 * The Risk Radar shows every cluster; this list is only meant to name the few
 * worth knowing about before setting off.
 */
const HOTSPOT_LIMIT = 3

/** A glyph per factor, matching the wording rather than decorating it. */
const FACTOR_ICONS: Record<RiskFactor['type'], string> = {
  rain: '☂',
  after_dark: '☾',
  high_speed_zone: '◎',
  significant_crash_history: '◈',
}

/**
 * Band a hotspot's crash count for its dot colour.
 *
 * The three bands match the concern palette, so a red dot on this list and a
 * high concern badge above it mean the same kind of thing.
 *
 * @param count - Recorded crashes in the cluster.
 * @returns The band name used as a CSS modifier.
 */
function crashBand(count: number): 'low' | 'med' | 'high' {
  if (count >= 20) return 'high'
  if (count >= 5) return 'med'
  return 'low'
}

/**
 * The line above the headline, e.g. "Tonight · 34 min drive".
 *
 * Says only what the response carries: the trip's own duration, and whether the
 * departure is today or on a later date.
 *
 * @param result - The trip check response.
 * @returns A short kicker string.
 */
function tripKicker(result: TripCheckResponse): string {
  const departure = new Date(result.departure_comparison.selected.departure_time)
  const now = new Date()
  const sameDay = departure.toDateString() === now.toDateString()
  const when = sameDay
    ? (departure.getHours() >= 18 || departure.getHours() < 5 ? 'Tonight' : 'Today')
    : new Intl.DateTimeFormat('en-AU', { weekday: 'long' }).format(departure)
  return `${when} · ${result.route.duration_minutes} min drive`
}

/**
 * Describe why a departure option carries its concern level.
 *
 * Prefers the backend's own phrasing, then the option's own factors. A backend
 * predating both still explains the selected option, whose conditions are the
 * trip's top-level factors; the later option has no such fallback, since its
 * conditions genuinely differ and must not be guessed at.
 *
 * @param option - The departure option to explain.
 * @param fallbackFactors - Factors to use when the option carries none.
 * @returns A short phrase, or null when nothing is known.
 */
function departureReason(
  option: DepartureComparisonOption,
  fallbackFactors?: RiskFactor[],
): string | null {
  if (option.reason) return option.reason
  const factors = option.factors?.length ? option.factors : fallbackFactors
  if (!factors?.length) return null
  return factors.map((factor) => SHORT_FACTOR_LABELS[factor.type]).join(', ')
}

/**
 * One departure option card, leading with the departure time.
 *
 * The time is the thing being chosen between, so it carries the visual weight
 * and the concern level sits beside it as a tag.
 *
 * @param props.label - Heading for the option ("Leave now" / "Leave later").
 * @param props.option - The departure option to render.
 * @param props.fallbackFactors - Factors to explain the level when the option carries none.
 * @param props.isLater - Tints the card as the alternative departure.
 * @returns The option card.
 */
function DepartureOptionCard({
  label,
  option,
  fallbackFactors,
  isLater = false,
}: {
  label: string
  option: DepartureComparisonOption
  fallbackFactors?: RiskFactor[]
  isLater?: boolean
}) {
  const reason = departureReason(option, fallbackFactors)

  return (
    <article className={isLater ? 'option later' : 'option'}>
      <p className="option-label">{label}</p>
      <div className="option-row">
        <strong className="option-time">{formatComparisonTime(option.departure_time)}</strong>
        <span className={`level level-${option.concern_level}`}>
          {CONCERN_WORDS[option.concern_level]}
        </span>
      </div>
      <p className="arrival">
        <span aria-hidden="true">◷</span>
        Arrive {formatComparisonTime(option.arrival_time)}
      </p>
      {/* Say why the tag reads as it does, so the level is never unexplained. */}
      {reason ? (
        <p className="departure-option-reason">Due to {reason}</p>
      ) : option.concern_level === 'low' ? (
        <p className="departure-option-reason">No concern conditions identified</p>
      ) : null}
    </article>
  )
}

/**
 * The completed result: concern banner, scale, conditions, comparison, spots.
 *
 * Split from the page itself so the page can show the empty state instead
 * without either branch having to duplicate the layout around it.
 *
 * @param props.result - A completed trip check.
 * @returns The result panel.
 */
function TripResultPanel({ result }: { result: TripCheckResponse }) {
  // Place names keyed by cluster id, filled in after the list can already be
  // read. The list never waits on the geocoder: counts render immediately and
  // each name replaces its fallback label as it arrives.
  const [hotspotNames, setHotspotNames] = useState<Record<number, string>>({})

  const [tripLesson, setTripLesson] = useState<Awaited<ReturnType<typeof getTripLesson>> | null>(null)
  const [tripLessonLoading, setTripLessonLoading] = useState(false)

  const hotspots = result.hotspots
  useEffect(() => {
    if (hotspots.length === 0) return

    const controller = new AbortController()
    reverseGeocodeAll(hotspots, controller.signal).then((labels) => {
      if (controller.signal.aborted) return
      const named: Record<number, string> = {}
      labels.forEach((label, index) => {
        if (label) named[hotspots[index].cluster_id] = label
      })
      if (Object.keys(named).length > 0) setHotspotNames(named)
    })

    return () => controller.abort()
  }, [hotspots])

  // Weather is not wired up on the backend yet, so a rain factor would be
  // asserting a condition nothing actually measured. Filtered here rather than
  // relying on the response to omit it.
//   const shownFactors = result.factors.filter((factor) => factor.type !== 'rain')
  const shownFactors = result.factors

  useEffect(() => {
  const riskFactors = result.factors.map((factor) => factor.type)
    if (riskFactors.length === 0) {
      setTripLesson(null)
      return
    }
    setTripLessonLoading(true)
    
    getTripLesson({
      risk_factors: riskFactors,
    })
      .then((lesson) => {
        setTripLesson(lesson)
      })
      .catch(() => {
        setTripLesson(null)
      })
      .finally(() => {
        setTripLessonLoading(false)
      })
  }, [result.factors])
  
    
  // A long route can return a dozen clusters, which buries the ones that
  // matter. Show the worst few by crash count and point at the Radar for the
  // rest; sorted here rather than trusting the response's order.
  const topHotspots = [...result.hotspots]
    .sort((a, b) => b.crash_count - a.crash_count)
    .slice(0, HOTSPOT_LIMIT)
  const hiddenHotspotCount = result.hotspots.length - topHotspots.length

  const dataMessage = partialDataMessage(result.data_status)

  // The destination label always exists, so the Radar search box is prefilled
  // even on backends that omit route coordinates; those simply cannot fly the
  // map to the destination, and open on the default view instead.
  const destinationPoint = result.route.destination_point
  const radarFocusState = {
    focus: {
      label: result.route.destination,
      longitude: destinationPoint?.longitude,
      latitude: destinationPoint?.latitude,
    },
  }

  return (
        <section className="card result-panel" aria-live="polite">
          <header className={`result-head level-${result.concern_level}`}>
            <div>
              <p className="result-kicker">{tripKicker(result)}</p>
              <h2>{CONCERN_HEADLINES[result.concern_level]}</h2>
              <p className="route-copy">
                {result.route.origin} <span aria-hidden="true">→</span> {result.route.destination}
              </p>
            </div>
            <div className="concern-block">
              <span>CONCERN</span>
              <strong>{CONCERN_WORDS[result.concern_level]}</strong>
            </div>
          </header>

          <div className="result-body">
            <TripRouteMap route={result.route} />
            <details className="means">
              <summary>
                <span className="means-icon" aria-hidden="true">ⓘ</span>
                What does this mean for my drive?
              </summary>
              <div className="means-body">
                {CONCERN_SCALE.map((step) => (
                  <div
                    key={step.level}
                    className={
                      step.level === result.concern_level
                        ? 'scale-row current'
                        : 'scale-row'
                    }
                    aria-current={step.level === result.concern_level ? 'true' : undefined}
                  >
                    <span className={`scale-tag scale-${step.level}`}>
                      {CONCERN_WORDS[step.level]}
                    </span>
                    <div>
                      <strong>{step.title}</strong>
                      <span>{step.detail}</span>
                    </div>
                  </div>
                ))}
                {/* <p className="means-foot">
                  Concern is based on conditions along your route at your departure
                  time, compared against recorded crash history for the same road and
                  hour. It is a description of the conditions, not a prediction about you.
                </p> */}
              </div>
            </details>

            <h3 className="condition-heading">What is affecting this trip</h3>
            {shownFactors.length > 0 ? (
              <ul className="conditions">
                {shownFactors.map((factor) => (
                  <li className="condition" key={factor.type}>
                    <span className="condition-label">
                      <span className="condition-icon" aria-hidden="true">
                        {FACTOR_ICONS[factor.type]}
                      </span>
                      {factor.label}
                    </span>
                    {factor.explanation && (
                      <details className="condition-why">
                        <summary>Why?</summary>
                        <p><strong>Source:</strong> {factor.explanation.source}</p>
                        <p><strong>Triggered by:</strong> {factor.explanation.trigger}</p>
                        {factor.explanation.limitation && (
                          <p><strong>Limitation:</strong> {factor.explanation.limitation}</p>
                        )}
                      </details>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-note">
                No concern conditions were identified for this trip.
              </p>
            )}

           {tripLessonLoading && (
             <section className="trip-prep" aria-live="polite">
               <p>Finding a short prep lesson for this trip…</p>
             </section>
           )}

           {!tripLessonLoading && tripLesson?.available && (
             <section className="trip-prep" aria-labelledby="trip-prep-title">
               <div className="trip-prep-heading">
                 <svg
                   viewBox="0 0 20 20"
                   fill="none"
                   stroke="currentColor"
                   strokeWidth="1.6"
                   strokeLinecap="round"
                   strokeLinejoin="round"
                   aria-hidden="true"
                 >
                   <path d="M3 4.5c2.3 0 4.3.6 7 2v10c-2.7-1.4-4.7-2-7-2V4.5Zm14 0c-2.3 0-4.3.6-7 2v10c2.7-1.4 4.7-2 7-2V4.5Z" />
                 </svg>
                 <h3 id="trip-prep-title">Prep this trip</h3>
               </div>

               <div className="trip-prep-topics">
                 {tripLesson.matched_topics.map((topic) => (
                   <span className="trip-prep-chip" key={topic}>
                     {topic.replaceAll('_', ' ')}
                   </span>
                 ))}
               </div>

               <Link
                 className="trip-prep-action"
                 to="/learn?mode=trip"
                 state={{ tripLesson }}
               >
                 <span aria-hidden="true">▶</span> 2-min prep
               </Link>
             </section>
           )}	

            <div className="compare-heading">
              <h3>Would later feel different?</h3>
              {/* <span>Same route · 30 min later</span> */}
            </div>
            <div className="options">
              <DepartureOptionCard
                label="Leave now"
                option={result.departure_comparison.selected}
                fallbackFactors={result.factors}
              />
              <DepartureOptionCard
                label="Leave later"
                option={result.departure_comparison.thirty_minutes_later}
                isLater
              />
            </div>
            {result.departure_comparison.difference_summary && (
              <p className="plain-explanation">
                <span aria-hidden="true">✦</span>
                {result.departure_comparison.difference_summary}
              </p>
            )}

            <div className="hotspots">
              <h3>Spots to watch on this route</h3>
              <p className="sub">
                {hiddenHotspotCount > 0
                  ? 'The most recorded crash clusters near your route, from 2012 to 2025'
                  : 'Recorded crash clusters near your route, from 2012 to 2025'}
              </p>
              {result.data_status.crash_data === 'unavailable' ? (
                <p className="empty-note">
                  Crash history is unavailable. No crash information has been inferred.
                </p>
              ) : result.hotspots.length === 0 ? (
                <p className="empty-note">
                  No major crash hotspots were found near this route.
                </p>
              ) : (
                <div className="spot-list">
                  {topHotspots.map((hotspot) => {
                    const name = hotspotNames[hotspot.cluster_id]
                    const location = hotspotLocationLabel(hotspot, result.route)
                    return (
                      <Link
                        className="spot"
                        key={hotspot.cluster_id}
                        to="/radar"
                        state={{
                          focus: {
                            label: name ?? `Cluster ${hotspot.cluster_id}`,
                            longitude: hotspot.longitude,
                            latitude: hotspot.latitude,
                            clusterId: hotspot.cluster_id,
                          },
                        }}
                      >
                        <span className={`dot ${crashBand(hotspot.crash_count)}`}>
                          {hotspot.crash_count}
                        </span>
                        <span className="spot-copy">
                          <strong>{name ?? `Cluster ${hotspot.cluster_id}`}</strong>
                          <span>
                            {hotspot.crash_count} recorded
                            {hotspot.crash_count === 1 ? ' crash' : ' crashes'}
                            {location ? ` · ${location}` : ''}
                          </span>
                        </span>
                        <span className="go">Open in Radar →</span>
                      </Link>
                    )
                  })}
                  {hiddenHotspotCount > 0 && (
                    <p className="spot-more">
                      {hiddenHotspotCount} more{' '}
                      {hiddenHotspotCount === 1 ? 'cluster ' : 'clusters '} 
                      near this route, {' '}
                      <Link to="/radar" state={radarFocusState}>see them all in Risk Radar →</Link>
                    </p>
                  )}
                </div>
              )}
            </div>

            {dataMessage && (
              <aside className="result-context-note warning">{dataMessage}</aside>
            )}

            {/* <div className="result-actions">
              <Link className="button button-secondary" to="/radar" state={radarFocusState}>
                View Risk Radar
              </Link>
              <Link className="text-button" to="/trip" onClick={clearResult}>
                Check another trip
              </Link>
            </div> */}
          </div>
        </section>
  )
}

/**
 * The trip screen: enter a trip on the left, read its result on the right.
 *
 * One screen rather than a form page and a separate result page, so changing a
 * trip never loses sight of the result it replaces. With nothing checked yet
 * the right-hand side explains what will appear there.
 *
 * @returns The trip screen.
 */
export default function TripPage() {
  const [result] = useTripResult()
  // Owned here rather than in the form, so the pending state can be shown
  // where the result will appear instead of in place of the form.
  const [isChecking, setIsChecking] = useState(false)

  return (
    <div className="trip-result-page page-container">
      {/* <header className="screen-header">
        <div>
          <p className="eyebrow">Trip check</p>

        </div>
      </header> */}

      <div className="trip-layout">
        <TripSearchForm
          submitLabel='Check my trip'
          initialOrigin={result?.route.origin ?? ''}
          initialDestination={result?.route.destination ?? ''}
          initialOriginPoint={result?.route.origin_point ?? null}
          initialDestinationPoint={result?.route.destination_point ?? null}
          showExample={!result}
          onLoadingChange={setIsChecking}
        />

        {/* While a check runs the result side shows the work in progress, even
            when an older result is still on screen, so it is clear the panel
            below is about to be replaced. */}
        {isChecking ? (
          <section className="card result-empty" aria-live="polite">
            <LoadingState message="Checking route and historical conditions…" />
          </section>
        ) : result ? (
          <TripResultPanel result={result} />
        ) : (
          <section className="card result-empty" aria-live="polite">
            <div>
              <h2>Nothing checked yet</h2>
              <p>Enter a trip on the Home screen, or use the form beside this one</p>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

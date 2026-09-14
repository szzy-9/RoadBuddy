import { useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { CRASH_COUNT_BANDS, UNAVAILABLE_CRASH_BAND, crashBand } from '../lib/crashBands'
import type { RouteSummary } from '../types/api'
import './TripRouteMap.css'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ''
const LEGEND_BANDS = [...CRASH_COUNT_BANDS, UNAVAILABLE_CRASH_BAND]
const LINE_COLOR: mapboxgl.ExpressionSpecification = [
  'match', ['get', 'band'],
  ...CRASH_COUNT_BANDS.flatMap(({ band, color }) => [band, color]),
  UNAVAILABLE_CRASH_BAND.color,
]

/** A result map of the ORS route; colours describe historical exposure only. */
export default function TripRouteMap({ route }: { route: RouteSummary }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [mapError, setMapError] = useState<string | null>(null)
  // A previously saved trip can predate the geometry fields.
  const hasGeometry = route.geometry?.coordinates.length >= 2

  useEffect(() => {
    const container = containerRef.current
    if (!MAPBOX_TOKEN || !hasGeometry || !container) return

    let map: mapboxgl.Map | undefined
    let observer: ResizeObserver | undefined
    const markers: mapboxgl.Marker[] = []
    setMapError(null)
    try {
      const data: mapboxgl.GeoJSONSourceSpecification['data'] = {
        type: 'FeatureCollection',
        features: (route.segments?.length ? route.segments : [{
          index: 0, geometry: route.geometry, nearby_crash_count: null,
        }]).map((segment) => ({
          type: 'Feature',
          geometry: segment.geometry,
          properties: {
            index: segment.index,
            nearbyCrashCount: segment.nearby_crash_count,
            band: crashBand(segment.nearby_crash_count).band,
          },
        })),
      }
      const bounds = new mapboxgl.LngLatBounds()
      route.geometry.coordinates.forEach((point) => bounds.extend(point))
      for (const point of [route.origin_point, route.destination_point]) {
        if (point) bounds.extend([point.longitude, point.latitude])
      }
      const routeMap = new mapboxgl.Map({
        container,
        accessToken: MAPBOX_TOKEN,
        style: 'mapbox://styles/mapbox/streets-v12',
        bounds,
        fitBoundsOptions: { padding: 55, maxZoom: 15, duration: 0 },
        scrollZoom: false,
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
        cooperativeGestures: true,
        renderWorldCopies: false,
        attributionControl: false,
      })
      map = routeMap
      routeMap.touchZoomRotate.disableRotation()
      routeMap.keyboard.disableRotation()
      routeMap.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-right')
      routeMap.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right')
      routeMap.on('error', () => {
        setMapError('The route map could not be loaded. The trip details are still available below.')
      })
      routeMap.on('load', () => {
        routeMap.addSource('trip-route', { type: 'geojson', data })
        routeMap.addLayer({
          id: 'trip-route-casing', type: 'line', source: 'trip-route',
          layout: { 'line-cap': 'round', 'line-join': 'round' },
          paint: { 'line-color': '#25383E', 'line-width': 11, 'line-opacity': 0.85 },
        })
        routeMap.addLayer({
          id: 'trip-route-exposure', type: 'line', source: 'trip-route',
          layout: { 'line-cap': 'round', 'line-join': 'round' },
          paint: { 'line-color': LINE_COLOR, 'line-width': 7 },
        })
      })
      for (const [label, point] of [
        ['START', route.origin_point], ['END', route.destination_point],
      ] as const) {
        if (!point) continue
        const element = document.createElement('div')
        element.className = `trip-route-marker trip-route-marker-${label.toLowerCase()}`
        element.textContent = label
        element.setAttribute('aria-label', `${label === 'START' ? 'Start' : 'End'} of trip`)
        markers.push(new mapboxgl.Marker({ element, anchor: 'bottom' })
          .setLngLat([point.longitude, point.latitude]).addTo(routeMap))
      }
      observer = new ResizeObserver(() => {
        routeMap.resize()
        routeMap.fitBounds(bounds, { padding: 55, maxZoom: 15, duration: 0 })
      })
      observer.observe(container)
    } catch {
      setMapError('The route map is unavailable in this browser. The trip details are still available below.')
    }
    return () => {
      observer?.disconnect()
      markers.forEach((marker) => marker.remove())
      map?.remove()
    }
  }, [route, hasGeometry])

  if (!MAPBOX_TOKEN || !hasGeometry) {
    return <p className="trip-route-unavailable" role="status">
      {!MAPBOX_TOKEN
        ? 'The route map is unavailable because a map access token has not been configured.'
        : 'Recheck this trip to load its route map.'}
    </p>
  }

  return (
    <section className="trip-route" aria-label="Trip route and historical crash exposure">
      <div ref={containerRef} className="trip-route-canvas" aria-label="Map of the driving route" />
      {mapError && <p className="trip-route-unavailable" role="status">{mapError}</p>}
      <div className="trip-route-legend">
        <h3>HISTORICAL CRASH EXPOSURE</h3>
        <ul>
          {LEGEND_BANDS.map(({ band, name, color, label }) => (
            <li key={band}>
              <span className="trip-route-swatch" style={{ backgroundColor: color }} aria-hidden="true" />
              <span>{name} <strong>{label}</strong></span>
            </li>
          ))}
        </ul>
        <p>Colours show recorded crash exposure near each part of the route, not a prediction of whether a crash will occur.</p>
      </div>
    </section>
  )
}

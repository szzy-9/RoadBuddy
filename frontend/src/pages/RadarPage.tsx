import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { getRadarCluster, getRadarClusters, searchLocations } from '../api/client'
import AddressAutocomplete from '../components/AddressAutocomplete'
import ClusterPanel from '../components/ClusterPanel'
import { bandColor, CRASH_COUNT_BANDS } from '../lib/crashBands'
import type {
  CrashClusterDetail,
  CrashClusterSummary,
  LocationSuggestion,
} from '../types/api'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ''

/** Melbourne CBD - the view the map opens on. */
const MELBOURNE_CBD: [number, number] = [144.9631, -37.8136]
const DEFAULT_ZOOM = 9.7
const FOCUS_ZOOM = 15

/** Zoom levels a search target may sit within before a move counts as nearby. */
const NEARBY_ZOOM_TOLERANCE = 1.5
/** Duration of the short pan used for a nearby move. */
const NEARBY_PAN_MS = 300
/** Grace period after a pan before the camera is forced to the target. */
const PAN_SETTLE_GRACE_MS = 150
/** Tolerance for deciding a pan actually reached its target. */
const ARRIVAL_EPSILON = 1e-4

/**
 * A place to open the map on, handed over from the trip result screen.
 *
 * Coordinates are optional: a backend predating them still supplies the label,
 * which prefills the search box even though the map cannot fly there.
 */
interface RadarFocus {
  label: string
  longitude?: number
  latitude?: number
}

interface RadarLocationState {
  focus?: RadarFocus
}

/**
 * Cap the number of rendered markers so low zooms stay readable.
 *
 * @param zoom - Current map zoom level.
 * @returns The maximum marker count to draw.
 */
function markerLimitForZoom(zoom: number): number {
  if (zoom < 10) return 8
  if (zoom < 12) return 20
  if (zoom < 14) return 50
  return 100
}

/**
 * Scale a marker by how many crashes it represents, bounded per zoom level.
 *
 * @param crashCount - Historical injury crashes in the cluster.
 * @param zoom - Current map zoom level.
 * @returns The marker diameter in pixels.
 */
function markerSize(crashCount: number, zoom: number): number {
  const minSize = zoom < 10 ? 12 : zoom < 12 ? 20 : 28
  const maxSize = zoom < 10 ? 18 : zoom < 12 ? 32 : 46
  return Math.max(minSize, Math.min(maxSize, minSize + Math.sqrt(crashCount) * 1.5))
}

/**
 * Risk Radar screen: a Mapbox map of historical crash clusters for Victoria.
 *
 * Opens on the trip destination when arriving from a trip result, otherwise on
 * Melbourne CBD. Markers are coloured by crash count using fixed bands.
 *
 * @returns The radar screen, or setup guidance when no Mapbox token is set.
 */
export default function RadarPage() {
  const location = useLocation()
  const focus = (location.state as RadarLocationState | null)?.focus ?? null
  const focusPoint: [number, number] | null =
    focus?.longitude !== undefined && focus.latitude !== undefined
      ? [focus.longitude, focus.latitude]
      : null

  const mapContainer = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const markerButtonsRef = useRef<Map<number, HTMLButtonElement>>(new Map())
  const markerObjectsRef = useRef<mapboxgl.Marker[]>([])
  const pendingSearchRef = useRef<number | null>(null)
  const searchSequenceRef = useRef(0)
  const viewportRequestSequenceRef = useRef(0)
  const selectClusterRef = useRef<(clusterId: number) => void>(() => {})

  const [clusters, setClusters] = useState<CrashClusterSummary[]>([])
  const [selected, setSelected] = useState<CrashClusterDetail | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [isClusterLoading, setIsClusterLoading] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)
  const [clusterError, setClusterError] = useState<string | null>(null)
  const [dataUnavailable, setDataUnavailable] = useState(false)
  const [roadQuery, setRoadQuery] = useState(focus?.label ?? '')
  const [showNoCrashHistory, setShowNoCrashHistory] = useState(false)

  /** Close the cluster detail sheet and drop any partially loaded detail. */
  const closeCluster = useCallback(() => {
    setSelected(null)
    setSelectedId(null)
    setClusterError(null)
    setIsClusterLoading(false)
  }, [])

  /**
   * Load and show the detail sheet for one crash cluster.
   *
   * @param clusterId - Identifier of the cluster to open.
   */
  const selectCluster = useCallback(async (clusterId: number) => {
    setSelectedId(clusterId)
    setSelected(null)
    setClusterError(null)
    setIsClusterLoading(true)
    try {
      setSelected(await getRadarCluster(clusterId))
    } catch (error) {
      setClusterError(error instanceof Error ? error.message : 'Could not load this crash cluster.')
    } finally {
      setIsClusterLoading(false)
    }
  }, [])

  // Marker click handlers are bound once at creation; routing through a ref
  // keeps them stable so selecting a cluster never rebuilds the marker layer.
  selectClusterRef.current = selectCluster

  /**
   * Move the map to a place and reload clusters for wherever it lands.
   *
   * Mapbox `flyTo` arcs: on a long move it zooms out, travels, then zooms back
   * in. That reads as the map throwing away the user's place before finding the
   * new one. Google Maps does not do this, so neither do we.
   *
   * The camera therefore cuts straight to the target unless the target is
   * already on screen at roughly the zoom we are settling at, in which case a
   * short pan keeps the surroundings legible. An instant cut is also the only
   * reliable option in a background tab, where browsers throttle the animation
   * loop and an animated move can silently never arrive.
   *
   * @param target - Coordinates to centre on.
   * @param zoom - Zoom level to settle at.
   * @param instant - Force a cut, skipping the on-screen pan.
   */
  const moveTo = useCallback((
    target: { longitude: number; latitude: number },
    zoom: number,
    { instant = false }: { instant?: boolean } = {},
  ) => {
    const map = mapRef.current
    if (!map) return

    map.stop()
    pendingSearchRef.current = ++searchSequenceRef.current
    const camera = { center: [target.longitude, target.latitude] as [number, number], zoom }

    const bounds = map.getBounds()
    const isNearby = !instant
      && bounds !== null
      && bounds.contains(camera.center)
      && Math.abs(map.getZoom() - zoom) <= NEARBY_ZOOM_TOLERANCE

    if (!isNearby) {
      map.jumpTo(camera)
      return
    }

    // Browsers throttle the animation loop in a background tab, where an eased
    // move can stall and strand the camera short of the target while the search
    // box already reads as the new place. Settle it outright if that happens.
    map.easeTo({ ...camera, duration: NEARBY_PAN_MS, essential: true })
    window.setTimeout(() => {
      if (mapRef.current !== map) return
      const settled = map.getCenter()
      const arrived = Math.abs(settled.lng - camera.center[0]) < ARRIVAL_EPSILON
        && Math.abs(settled.lat - camera.center[1]) < ARRIVAL_EPSILON
        && Math.abs(map.getZoom() - zoom) < ARRIVAL_EPSILON
      if (!arrived) map.jumpTo(camera)
    }, NEARBY_PAN_MS + PAN_SETTLE_GRACE_MS)
  }, [])

  /**
   * Handle a pick from the road search box.
   *
   * @param suggestion - The chosen location.
   */
  const selectRoadLocation = useCallback((suggestion: LocationSuggestion) => {
    closeCluster()
    setShowNoCrashHistory(false)
    moveTo(suggestion, FOCUS_ZOOM)
  }, [closeCluster, moveTo])

  /**
   * Handle search-box edits.
   *
   * Clearing the box clears the search, not the view. Snapping back to
   * Melbourne would throw away wherever the user had panned to, which is never
   * what emptying a text field is asking for.
   *
   * @param value - The new search text.
   */
  const handleQueryChange = useCallback((value: string) => {
    setRoadQuery(value)
    if (value.trim() !== '') return

    closeCluster()
    setShowNoCrashHistory(false)
  }, [closeCluster])

  // Create the map once. Cluster loading lives here because it is driven by
  // Mapbox events rather than React state.
  useEffect(() => {
    if (!MAPBOX_TOKEN || !mapContainer.current || mapRef.current) return

    mapboxgl.accessToken = MAPBOX_TOKEN
    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: focusPoint ?? MELBOURNE_CBD,
      zoom: focusPoint ? FOCUS_ZOOM : DEFAULT_ZOOM,
      minZoom: 5.5,
      maxBounds: [[140, -39.5], [150, -33]],
      renderWorldCopies: false,
      // The legend holds the bottom-left corner and the search box floats over
      // the top left, so the logo sits bottom-right with the attribution.
      // Both must stay visible to satisfy the Mapbox licence.
      attributionControl: false,
      logoPosition: 'bottom-right',
    })
    mapRef.current = map
    setIsMapReady(true)
    if (import.meta.env.DEV) {
      (window as unknown as { __radarMap?: mapboxgl.Map }).__radarMap = map
    }
    map.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-right')
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right')

    const loadViewport = async (searchedAreaId: number | null) => {
      const requestId = ++viewportRequestSequenceRef.current
      if (searchedAreaId === null) setShowNoCrashHistory(false)

      const bounds = map.getBounds()
      if (!bounds) return
      const bbox = [
        bounds.getWest(),
        bounds.getSouth(),
        bounds.getEast(),
        bounds.getNorth(),
      ].map((value) => value.toFixed(6)).join(',')

      try {
        const zoom = map.getZoom()
        const response = await getRadarClusters(bbox, zoom)
        if (requestId !== viewportRequestSequenceRef.current) return

        setClusters(response.clusters.slice(0, markerLimitForZoom(zoom)))
        setDataUnavailable(response.data_status === 'unavailable')
        setMapError(null)
        setShowNoCrashHistory(
          searchedAreaId !== null
          && searchedAreaId === searchSequenceRef.current
          && response.data_status === 'available'
          && response.clusters.length === 0,
        )
      } catch (error) {
        if (requestId !== viewportRequestSequenceRef.current) return

        setShowNoCrashHistory(false)
        setMapError(error instanceof Error ? error.message : 'Could not load crash clusters.')
      }
    }

    // Arriving from a trip result counts as a search, so an empty destination
    // area reports "no recorded crash history" rather than staying silent.
    if (focusPoint) pendingSearchRef.current = ++searchSequenceRef.current

    map.on('load', () => void loadViewport(pendingSearchRef.current))
    map.on('moveend', () => {
      const searchedAreaId = pendingSearchRef.current
      pendingSearchRef.current = null
      void loadViewport(searchedAreaId)
    })
    map.on('error', () => setMapError('The map could not be loaded. Check the Mapbox token and try again.'))

    return () => {
      markerObjectsRef.current.forEach((marker) => marker.remove())
      markerObjectsRef.current = []
      markerButtonsRef.current.clear()
      map.remove()
      mapRef.current = null
      setIsMapReady(false)
    }
    // Runs once: `focus` is read only for the initial camera position.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // A focus label without coordinates (older backends omit them) is resolved
  // here, so arriving from a trip result still zooms to the destination.
  //
  // The lookup is keyed by label rather than guarded by a "done" flag: React
  // StrictMode double-invokes effects in development, and marking the work done
  // before the map exists would drop the fly entirely.
  const [resolvedFocus, setResolvedFocus] = useState<[number, number] | null>(null)
  const [isMapReady, setIsMapReady] = useState(false)

  useEffect(() => {
    if (!focus || focusPoint || !MAPBOX_TOKEN) return

    let cancelled = false
    void (async () => {
      try {
        const response = await searchLocations(focus.label)
        const match = response.suggestions[0]
        if (cancelled || !match) return
        setResolvedFocus([match.longitude, match.latitude])
      } catch {
        // Leave the map on its default view; the search box is still prefilled.
      }
    })()
    return () => { cancelled = true }
  }, [focus, focusPoint])

  // The map now sizes itself from the viewport, so its container changes shape
  // on rotation, window resize, and when the mobile browser's address bar
  // collapses. Mapbox only reads its container size when told to, so without
  // this the canvas keeps the size it had on the first paint.
  useEffect(() => {
    const container = mapContainer.current
    if (!container || !isMapReady) return

    const observer = new ResizeObserver(() => mapRef.current?.resize())
    observer.observe(container)
    return () => observer.disconnect()
  }, [isMapReady])

  // Fly once both the resolved point and the map are available. Ordering is not
  // guaranteed: the lookup can finish before or after the map is constructed.
  const hasFlownToFocusRef = useRef(false)
  useEffect(() => {
    if (!resolvedFocus || hasFlownToFocusRef.current || !isMapReady || !mapRef.current) return
    hasFlownToFocusRef.current = true
    moveTo(
      { longitude: resolvedFocus[0], latitude: resolvedFocus[1] },
      FOCUS_ZOOM,
      { instant: true },
    )
  }, [resolvedFocus, moveTo, isMapReady])

  // Rebuild markers only when the cluster set itself changes.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    markerObjectsRef.current.forEach((marker) => marker.remove())
    markerButtonsRef.current.clear()

    const zoom = map.getZoom()
    markerObjectsRef.current = clusters.map((cluster) => {
      const markerRoot = document.createElement('div')
      markerRoot.className = 'radar-marker-root'

      const button = document.createElement('button')
      button.type = 'button'
      button.className = 'radar-marker'
      button.setAttribute(
        'aria-label',
        `${cluster.crash_count} historical injury crashes in this area`,
      )
      const size = markerSize(cluster.crash_count, zoom)
      button.textContent = zoom >= 10 ? String(cluster.crash_count) : ''
      button.style.width = `${size}px`
      button.style.height = `${size}px`
      button.style.backgroundColor = bandColor(cluster.crash_count)
      button.addEventListener('click', () => void selectClusterRef.current(cluster.id))

      markerRoot.appendChild(button)
      markerButtonsRef.current.set(cluster.id, button)
      return new mapboxgl.Marker({ element: markerRoot })
        .setLngLat([cluster.longitude, cluster.latitude])
        .addTo(map)
    })
  }, [clusters])

  // Selection is a class toggle on existing nodes, not a marker rebuild.
  useEffect(() => {
    markerButtonsRef.current.forEach((button, clusterId) => {
      button.classList.toggle('selected', clusterId === selectedId)
    })
  }, [clusters, selectedId])

  useEffect(() => {
    if (selectedId === null) return

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeCluster()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [closeCluster, selectedId])

  return (
    <div className="radar-page">
      {!MAPBOX_TOKEN ? (
        <div className="map-token-message">
          <span aria-hidden="true">⌖</span>
          <h2>Add a Mapbox public token to show the radar</h2>
          <p>Set <code>VITE_MAPBOX_TOKEN</code> in <code>frontend/.env</code>, then restart the frontend.</p>
        </div>
      ) : (
        <div className="radar-layout">
          <div className="map-card">
            <div ref={mapContainer} className="map-container" aria-label="Map of historical crash clusters" />
            {/* Floated over the map rather than stacked above it, so the map
                itself keeps the full height of the screen. */}
            <div className="radar-search">
              <AddressAutocomplete
                label=""
                value={roadQuery}
                onChange={handleQueryChange}
                onSelect={selectRoadLocation}
                placeholder="Search a suburb, road or postcode"
                initialValueIsSelected={focus !== null}
              />
            </div>
            <div className="map-legend">
              <span className="map-legend-title">Crashes</span>
              <ul className="map-legend-scale">
                {CRASH_COUNT_BANDS.map((band) => (
                  <li key={band.label}>
                    <span
                      className="map-legend-swatch"
                      style={{ backgroundColor: band.color }}
                      aria-hidden="true"
                    />
                    {band.label}
                  </li>
                ))}
              </ul>
            </div>
            {(mapError || dataUnavailable) && (
              <div className="radar-status-message" role="status">
                {mapError || 'Crash data is currently unavailable. No crash information is being inferred.'}
              </div>
            )}
            {showNoCrashHistory && (
              <div className="radar-no-history" role="status">
                <strong>No recorded crash history</strong>
                <span>No recorded crashes were found for this road in the available dataset. This does not mean the road is risk-free.</span>
              </div>
            )}
            {selectedId !== null && (
              <div className="radar-sheet-backdrop" onMouseDown={closeCluster}>
                <div className="radar-sheet" onMouseDown={(event) => event.stopPropagation()}>
                  <ClusterPanel
                    cluster={selected}
                    isLoading={isClusterLoading}
                    error={clusterError}
                    onClose={closeCluster}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { getRadarCluster, getRadarClusters, searchLocations } from '../api/client'
import AddressAutocomplete from '../components/AddressAutocomplete'
import ClusterPanel from '../components/ClusterPanel'
import type {
  CrashClusterDetail,
  CrashClusterSummary,
  LocationSuggestion,
} from '../types/api'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ''

/** Melbourne CBD - the default view, and where clearing the search returns to. */
const MELBOURNE_CBD: [number, number] = [144.9631, -37.8136]
const DEFAULT_ZOOM = 9.7
const FOCUS_ZOOM = 15

/**
 * Five-band intensity scale for crash counts.
 *
 * Thresholds are fixed rather than derived from the visible clusters, so a
 * colour means the same thing at every zoom and in every suburb. Edit `min`
 * to retune the bands; each band covers `min` up to the next band's `min`.
 */
const CRASH_COUNT_BANDS = [
  { min: 0, color: '#2E9E5B', label: '1-4' },
  { min: 5, color: '#E5B917', label: '5-9' },
  { min: 10, color: '#E8843C', label: '10-19' },
  { min: 20, color: '#D6453D', label: '20-49' },
  { min: 50, color: '#A63BC4', label: '50+' },
] as const

/**
 * Pick the colour band for a crash count.
 *
 * @param crashCount - Historical injury crashes in the cluster.
 * @returns The matching band's colour.
 */
function bandColor(crashCount: number): string {
  let color: string = CRASH_COUNT_BANDS[0].color
  for (const band of CRASH_COUNT_BANDS) {
    if (crashCount >= band.min) color = band.color
  }
  return color
}

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
   * Fly the map to a place and reload clusters for wherever it lands.
   *
   * @param target - Coordinates to centre on.
   * @param zoom - Zoom level to settle at.
   */
  const flyTo = useCallback((
    target: { longitude: number; latitude: number },
    zoom: number,
    { animate = true }: { animate?: boolean } = {},
  ) => {
    const map = mapRef.current
    if (!map) return

    map.stop()
    pendingSearchRef.current = ++searchSequenceRef.current
    const camera = { center: [target.longitude, target.latitude] as [number, number], zoom }
    // jumpTo does not depend on the animation loop, which browsers throttle in
    // a background tab; flyTo would silently leave the camera where it was.
    if (animate) map.flyTo({ ...camera, essential: false })
    else map.jumpTo(camera)
  }, [])

  /**
   * Handle a pick from the road search box.
   *
   * @param suggestion - The chosen location.
   */
  const selectRoadLocation = useCallback((suggestion: LocationSuggestion) => {
    closeCluster()
    setShowNoCrashHistory(false)
    flyTo(suggestion, FOCUS_ZOOM)
  }, [closeCluster, flyTo])

  /**
   * Handle search-box edits, returning to Melbourne CBD once it is cleared.
   *
   * @param value - The new search text.
   */
  const handleQueryChange = useCallback((value: string) => {
    setRoadQuery(value)
    if (value.trim() !== '') return

    closeCluster()
    setShowNoCrashHistory(false)
    flyTo(
      { longitude: MELBOURNE_CBD[0], latitude: MELBOURNE_CBD[1] },
      DEFAULT_ZOOM,
    )
  }, [closeCluster, flyTo])

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
      // The legend takes the bottom-left corner, so the logo moves to the top
      // left and the attribution is added below at bottom-right. Both must stay
      // visible to satisfy the Mapbox licence.
      attributionControl: false,
      logoPosition: 'top-left',
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

  // Fly once both the resolved point and the map are available. Ordering is not
  // guaranteed: the lookup can finish before or after the map is constructed.
  const hasFlownToFocusRef = useRef(false)
  useEffect(() => {
    if (!resolvedFocus || hasFlownToFocusRef.current || !isMapReady || !mapRef.current) return
    hasFlownToFocusRef.current = true
    flyTo(
      { longitude: resolvedFocus[0], latitude: resolvedFocus[1] },
      FOCUS_ZOOM,
      { animate: false },
    )
  }, [resolvedFocus, flyTo, isMapReady])

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

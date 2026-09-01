import { useCallback, useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { getRadarCluster, getRadarClusters } from '../api/client'
import AddressAutocomplete from '../components/AddressAutocomplete'
import ClusterPanel from '../components/ClusterPanel'
import type {
  CrashClusterDetail,
  CrashClusterSummary,
  LocationSuggestion,
} from '../types/api'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ''

export default function RadarPage() {
  const mapContainer = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const markersRef = useRef<mapboxgl.Marker[]>([])
  const pendingSearchRef = useRef<number | null>(null)
  const searchSequenceRef = useRef(0)
  const viewportRequestSequenceRef = useRef(0)
  const [clusters, setClusters] = useState<CrashClusterSummary[]>([])
  const [selected, setSelected] = useState<CrashClusterDetail | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [isClusterLoading, setIsClusterLoading] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)
  const [clusterError, setClusterError] = useState<string | null>(null)
  const [dataUnavailable, setDataUnavailable] = useState(false)
  const [roadQuery, setRoadQuery] = useState('')
  const [showNoCrashHistory, setShowNoCrashHistory] = useState(false)

  const closeCluster = useCallback(() => {
    setSelected(null)
    setSelectedId(null)
    setClusterError(null)
    setIsClusterLoading(false)
  }, [])

  const selectRoadLocation = useCallback((suggestion: LocationSuggestion) => {
    closeCluster()
    setShowNoCrashHistory(false)

    const map = mapRef.current
    if (!map) return

    map.stop()
    pendingSearchRef.current = ++searchSequenceRef.current
    map.flyTo({
      center: [suggestion.longitude, suggestion.latitude],
      zoom: 15,
      essential: false,
    })
  }, [closeCluster])

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

  useEffect(() => {
    if (!MAPBOX_TOKEN || !mapContainer.current || mapRef.current) return

    mapboxgl.accessToken = MAPBOX_TOKEN
    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [144.9631, -37.8136],
      zoom: 9.7,
      minZoom: 5.5,
      maxBounds: [[140, -39.5], [150, -33]],
      renderWorldCopies: false,
      attributionControl: true,
    })
    mapRef.current = map
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

        const maxMarkers =
          zoom < 10 ? 8 :
          zoom < 12 ? 20 :
          zoom < 14 ? 50 :
          100

        setClusters(response.clusters.slice(0, maxMarkers))	

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

    map.on('load', () => void loadViewport(null))
    map.on('moveend', () => {
      const searchedAreaId = pendingSearchRef.current
      pendingSearchRef.current = null
      void loadViewport(searchedAreaId)
    })
    map.on('error', () => setMapError('The map could not be loaded. Check the Mapbox token and try again.'))

    return () => {
      markersRef.current.forEach((marker) => marker.remove())
      markersRef.current = []
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current = clusters.map((cluster) => {
      const markerRoot = document.createElement('div')
      markerRoot.className = 'radar-marker-root'
      const button = document.createElement('button')
      button.type = 'button'
      button.className = `radar-marker${selectedId === cluster.id ? ' selected' : ''}`
      button.setAttribute('aria-label', `${cluster.crash_count} historical injury crashes in this area`)
      const zoom = map.getZoom()

      const minSize = zoom < 10 ? 12 : zoom < 12 ? 20 : 28
      const maxSize = zoom < 10 ? 18 : zoom < 12 ? 32 : 46

      const size = Math.max(
        minSize,
        Math.min(maxSize, minSize + Math.sqrt(cluster.crash_count) * 1.5),
      )

      button.textContent = zoom >= 10 ? String(cluster.crash_count) : ''
      button.style.width = `${size}px`
      button.style.height = `${size}px`
      button.addEventListener('click', () => void selectCluster(cluster.id))
      markerRoot.appendChild(button)
      return new mapboxgl.Marker({ element: markerRoot })
        .setLngLat([cluster.longitude, cluster.latitude])
        .addTo(map)
    })
  }, [clusters, selectedId, selectCluster])

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
          onChange={setRoadQuery}
          onSelect={selectRoadLocation}
          placeholder="Search a road"
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
            <div className="map-legend"><span /> Marker size reflects crash count</div>
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

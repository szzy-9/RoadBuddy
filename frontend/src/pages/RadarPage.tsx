import { useCallback, useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { getRadarCluster, getRadarClusters } from '../api/client'
import ClusterPanel from '../components/ClusterPanel'
import ErrorMessage from '../components/ErrorMessage'
import type { CrashClusterDetail, CrashClusterSummary } from '../types/api'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ''

export default function RadarPage() {
  const mapContainer = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const markersRef = useRef<mapboxgl.Marker[]>([])
  const [clusters, setClusters] = useState<CrashClusterSummary[]>([])
  const [selected, setSelected] = useState<CrashClusterDetail | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [isClusterLoading, setIsClusterLoading] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)
  const [clusterError, setClusterError] = useState<string | null>(null)
  const [dataUnavailable, setDataUnavailable] = useState(false)

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

    const loadViewport = async () => {
      const bounds = map.getBounds()
      if (!bounds) return
      const bbox = [
        bounds.getWest(),
        bounds.getSouth(),
        bounds.getEast(),
        bounds.getNorth(),
      ].map((value) => value.toFixed(6)).join(',')
      try {
        const response = await getRadarClusters(bbox)
        setClusters(response.clusters)
        setDataUnavailable(response.data_status === 'unavailable')
        setMapError(null)
      } catch (error) {
        setMapError(error instanceof Error ? error.message : 'Could not load crash clusters.')
      }
    }

    map.on('load', loadViewport)
    map.on('moveend', loadViewport)
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
      const button = document.createElement('button')
      button.type = 'button'
      button.className = `radar-marker${selectedId === cluster.id ? ' selected' : ''}`
      button.setAttribute('aria-label', `${cluster.crash_count} crashes near ${cluster.name || 'this location'}`)
      button.textContent = String(cluster.crash_count)
      const size = Math.max(36, Math.min(62, 30 + Math.sqrt(cluster.crash_count) * 7))
      button.style.width = `${size}px`
      button.style.height = `${size}px`
      button.addEventListener('click', () => void selectCluster(cluster.id))
      return new mapboxgl.Marker({ element: button })
        .setLngLat([cluster.longitude, cluster.latitude])
        .addTo(map)
    })
  }, [clusters, selectedId, selectCluster])

  return (
    <div className="radar-page">
      <section className="radar-heading">
        <div>
          <p className="eyebrow">Risk Radar</p>
          <h1>Explore crash history around you.</h1>
        </div>
        <div className="layer-chip"><span aria-hidden="true" /> Crashes</div>
      </section>

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
          </div>
          <ClusterPanel
            cluster={selected}
            isLoading={isClusterLoading}
            error={clusterError}
            onClose={() => { setSelected(null); setSelectedId(null); setClusterError(null) }}
          />
        </div>
      )}

      {mapError && <ErrorMessage message={mapError} />}
      {dataUnavailable && (
        <ErrorMessage message="Crash data is currently unavailable. No crash information is being inferred." />
      )}
    </div>
  )
}

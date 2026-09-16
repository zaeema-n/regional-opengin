import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const SRI_LANKA_BOUNDS = [
  [5.85, 79.4],
  [9.9, 82.0],
]
const HIGHLIGHT_STYLE = {
  color: '#1d4ed8',
  weight: 2,
  fillColor: '#3b82f6',
  fillOpacity: 0.3,
}

export default function RegionMap({ geojson }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const layerRef = useRef(null)

  useEffect(() => {
    if (mapRef.current || !containerRef.current) {
      return undefined
    }

    const map = L.map(containerRef.current, { zoomControl: false })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)
    L.control.zoom({ position: 'topright' }).addTo(map)
    map.fitBounds(SRI_LANKA_BOUNDS, { padding: [24, 24] })
    mapRef.current = map
    const invalidate = () => map.invalidateSize()
    requestAnimationFrame(() => {
      map.invalidateSize()
      map.fitBounds(SRI_LANKA_BOUNDS, { padding: [24, 24] })
    })
    window.addEventListener('resize', invalidate)

    return () => {
      window.removeEventListener('resize', invalidate)
      map.remove()
      mapRef.current = null
      layerRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) {
      return
    }

    if (layerRef.current) {
      map.removeLayer(layerRef.current)
      layerRef.current = null
    }

    if (!geojson) {
      return
    }

    const layer = L.geoJSON(geojson, { style: HIGHLIGHT_STYLE }).addTo(map)
    layerRef.current = layer
    const bounds = layer.getBounds()
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [32, 32] })
    }
    map.invalidateSize()
  }, [geojson])

  return <div ref={containerRef} className="h-full w-full" />
}

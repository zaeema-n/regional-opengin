import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const SRI_LANKA_CENTER = [7.8731, 80.7718]
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
    map.setView(SRI_LANKA_CENTER, 7)
    mapRef.current = map
    const invalidate = () => map.invalidateSize()
    requestAnimationFrame(invalidate)
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

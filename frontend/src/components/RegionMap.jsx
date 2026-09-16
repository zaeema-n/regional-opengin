import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const SRI_LANKA_BOUNDS = [
  [5.85, 79.4],
  [9.9, 82.0],
]
const SELECTED_STYLE = {
  color: '#1d4ed8',
  weight: 3,
  fillColor: '#3b82f6',
  fillOpacity: 0.22,
}
const OUTLINE_STYLE = {
  color: '#334155',
  weight: 1,
  fillColor: '#94a3b8',
  fillOpacity: 0.08,
}
const HOVER_STYLE = {
  color: '#c2410c',
  weight: 3,
  fillColor: '#f97316',
  fillOpacity: 0.45,
}

function syncLayer(map, layerRef, geojson, { style, pane, fitBounds = false } = {}) {
  if (layerRef.current) {
    map.removeLayer(layerRef.current)
    layerRef.current = null
  }
  if (!geojson) {
    return
  }
  const layer = L.geoJSON(geojson, {
    style,
    pane,
    interactive: false,
  }).addTo(map)
  layerRef.current = layer
  if (fitBounds) {
    const bounds = layer.getBounds()
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [32, 32] })
    }
  }
}

export default function RegionMap({ geojson, outlineGeojson, hoverGeojson }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const selectedLayerRef = useRef(null)
  const outlineLayerRef = useRef(null)
  const hoverLayerRef = useRef(null)
  const previewFitRef = useRef(false)

  useEffect(() => {
    if (mapRef.current || !containerRef.current) {
      return undefined
    }

    const map = L.map(containerRef.current, { zoomControl: false })
    map.createPane('region-outlines')
    map.getPane('region-outlines').style.zIndex = 410
    map.createPane('region-hover')
    map.getPane('region-hover').style.zIndex = 450
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
      if (!selectedLayerRef.current) {
        map.fitBounds(SRI_LANKA_BOUNDS, { padding: [24, 24] })
      }
    })
    window.addEventListener('resize', invalidate)

    return () => {
      window.removeEventListener('resize', invalidate)
      map.remove()
      mapRef.current = null
      selectedLayerRef.current = null
      outlineLayerRef.current = null
      hoverLayerRef.current = null
      previewFitRef.current = false
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) {
      return
    }
    syncLayer(map, selectedLayerRef, geojson, {
      style: SELECTED_STYLE,
      fitBounds: true,
    })
    map.invalidateSize()
  }, [geojson])

  useEffect(() => {
    const map = mapRef.current
    if (!map) {
      return
    }
    syncLayer(map, outlineLayerRef, outlineGeojson, {
      style: OUTLINE_STYLE,
      pane: 'region-outlines',
    })
  }, [outlineGeojson])

  useEffect(() => {
    const map = mapRef.current
    if (!map) {
      return
    }
    syncLayer(map, hoverLayerRef, hoverGeojson, {
      style: HOVER_STYLE,
      pane: 'region-hover',
    })
    if (hoverLayerRef.current) {
      const hoverBounds = hoverLayerRef.current.getBounds()
      if (
        hoverBounds.isValid() &&
        !map.getBounds().contains(hoverBounds.getCenter())
      ) {
        previewFitRef.current = true
        map.fitBounds(hoverBounds, { padding: [32, 32] })
      }
      return
    }
    if (previewFitRef.current && selectedLayerRef.current) {
      previewFitRef.current = false
      const selectedBounds = selectedLayerRef.current.getBounds()
      if (selectedBounds.isValid()) {
        map.fitBounds(selectedBounds, { padding: [32, 32] })
      }
    }
  }, [hoverGeojson])

  return <div ref={containerRef} className="h-full w-full" />
}

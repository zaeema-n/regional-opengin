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
  className: 'region-outline',
}
const HOVER_STYLE = {
  color: '#c2410c',
  weight: 3,
  fillColor: '#f97316',
  fillOpacity: 0.45,
  className: 'region-outline',
}

function featureId(feature) {
  return feature?.id ?? feature?.properties?.id ?? null
}

function featureName(feature) {
  return feature?.properties?.name ?? null
}

function outlineStyle(feature, hoveredId) {
  return hoveredId && featureId(feature) === hoveredId
    ? HOVER_STYLE
    : OUTLINE_STYLE
}

function syncLayer(map, layerRef, geojson, { style, pane, fitBounds = false, interactive = false, onEachFeature } = {}) {
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
    interactive,
    onEachFeature,
  }).addTo(map)
  layerRef.current = layer
  if (fitBounds) {
    const bounds = layer.getBounds()
    if (bounds.isValid()) {
      map.flyToBounds(bounds, { padding: [32, 32], duration: 0.7 })
    }
  }
}

function bringHoverToFront(featureLayer) {
  const el = featureLayer.getElement?.()
  if (el?.parentNode?.lastChild === el) {
    return
  }
  featureLayer.bringToFront()
}

function paintHover(layer, hoveredId) {
  if (!layer) {
    return
  }
  layer.eachLayer((featureLayer) => {
    featureLayer.setStyle(outlineStyle(featureLayer.feature, hoveredId))
    if (hoveredId && featureId(featureLayer.feature) === hoveredId) {
      bringHoverToFront(featureLayer)
      if (featureLayer.getTooltip()) {
        featureLayer.openTooltip()
      }
    } else if (featureLayer.getTooltip()) {
      featureLayer.closeTooltip()
    }
  })
}

function placeZoomControl(map) {
  map.getContainer()
    .querySelectorAll('.leaflet-control-zoom')
    .forEach((node) => node.remove())
  L.control.zoom({ position: 'bottomright' }).addTo(map)
}

export default function RegionMap({
  geojson,
  outlineGeojson,
  hoveredId,
  onHoverFeature,
  onSelectFeature,
}) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const selectedLayerRef = useRef(null)
  const outlineLayerRef = useRef(null)
  const hoveredIdRef = useRef(hoveredId)
  const onHoverRef = useRef(onHoverFeature)
  const onSelectRef = useRef(onSelectFeature)

  useEffect(() => {
    hoveredIdRef.current = hoveredId
  }, [hoveredId])

  useEffect(() => {
    onHoverRef.current = onHoverFeature
  }, [onHoverFeature])

  useEffect(() => {
    onSelectRef.current = onSelectFeature
  }, [onSelectFeature])

  useEffect(() => {
    if (mapRef.current || !containerRef.current) {
      return undefined
    }

    const map = L.map(containerRef.current, { zoomControl: false })
    map.createPane('region-outlines')
    map.getPane('region-outlines').style.zIndex = 410
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)
    map.fitBounds(SRI_LANKA_BOUNDS, { padding: [24, 24] })
    mapRef.current = map
    const invalidate = () => map.invalidateSize()
    const clearHover = () => onHoverRef.current?.(null)
    requestAnimationFrame(() => {
      map.invalidateSize()
      if (!selectedLayerRef.current) {
        map.fitBounds(SRI_LANKA_BOUNDS, { padding: [24, 24] })
      }
    })
    window.addEventListener('resize', invalidate)
    map.getContainer().addEventListener('mouseleave', clearHover)

    return () => {
      window.removeEventListener('resize', invalidate)
      map.getContainer().removeEventListener('mouseleave', clearHover)
      map.remove()
      mapRef.current = null
      selectedLayerRef.current = null
      outlineLayerRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) {
      return
    }
    placeZoomControl(map)
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
      style: (feature) => outlineStyle(feature, hoveredIdRef.current),
      pane: 'region-outlines',
      interactive: true,
      onEachFeature: (feature, layer) => {
        const id = featureId(feature)
        const name = featureName(feature)
        if (name) {
          layer.bindTooltip(name, {
            sticky: true,
            direction: 'top',
            opacity: 0.95,
            className: 'region-name-tooltip',
          })
        }
        layer.on({
          mouseover: () => {
            if (id) {
              onHoverRef.current?.(id)
            }
          },
          mouseout: (event) => {
            const related = event.originalEvent?.relatedTarget
            if (
              !related ||
              related.closest?.('.leaflet-region-outlines-pane')
            ) {
              return
            }
            onHoverRef.current?.(null)
          },
          click: (event) => {
            L.DomEvent.stopPropagation(event)
            if (id) {
              onSelectRef.current?.(id)
            }
          },
        })
      },
    })
    paintHover(outlineLayerRef.current, hoveredIdRef.current)
  }, [outlineGeojson])

  useEffect(() => {
    paintHover(outlineLayerRef.current, hoveredId)
  }, [hoveredId])

  return <div ref={containerRef} className="h-full w-full" />
}

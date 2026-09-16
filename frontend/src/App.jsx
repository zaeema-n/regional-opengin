import NavPanel from './components/NavPanel.jsx'
import RegionMap from './components/RegionMap.jsx'
import { useRegionStack } from './hooks/useRegionStack.js'

export default function App() {
  const {
    stack,
    status,
    error,
    dropdown,
    childrenCache,
    hydrating,
    mapGeojson,
    outlineGeojson,
    hoverGeojson,
    hoveredChild,
    openRelation,
    selectChild,
    hoverChild,
    back,
    reset,
    retry,
  } = useRegionStack()

  return (
    <div className="relative h-full w-full overflow-hidden">
      <RegionMap
        geojson={mapGeojson}
        outlineGeojson={outlineGeojson}
        hoverGeojson={hoverGeojson}
      />
      <NavPanel
        stack={stack}
        status={status}
        error={error}
        dropdown={dropdown}
        childrenCache={childrenCache}
        hydrating={hydrating}
        hoveredChildId={hoveredChild?.id}
        onOpenRelation={openRelation}
        onSelectChild={selectChild}
        onHoverChild={hoverChild}
        onBack={back}
        onReset={reset}
        onRetry={retry}
      />
    </div>
  )
}

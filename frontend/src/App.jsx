import NavPanel from './components/NavPanel.jsx'
import RegionMap from './components/RegionMap.jsx'
import StatsPanel from './components/StatsPanel.jsx'
import { useRegionStack } from './hooks/useRegionStack.js'

export default function App() {
  const {
    stack,
    status,
    error,
    dropdown,
    childrenCache,
    hydrating,
    selectedRegion,
    mapGeojson,
    outlineGeojson,
    hoveredChild,
    openRelation,
    selectChild,
    hoverChild,
    back,
    reset,
    goTo,
    retry,
  } = useRegionStack()

  const statsRegion = hoveredChild ?? selectedRegion

  return (
    <div className="relative h-full w-full overflow-hidden">
      <RegionMap
        geojson={mapGeojson}
        outlineGeojson={outlineGeojson}
        hoveredId={hoveredChild?.id}
      />
      <div className="absolute top-4 left-4 z-1000 flex max-h-[calc(100%-2rem)] w-96 flex-col overflow-hidden">
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
          onGoTo={goTo}
          onRetry={retry}
        />
      </div>
      <div className="absolute top-4 right-4 z-1000 w-80">
        <StatsPanel
          region={statsRegion}
          preview={Boolean(hoveredChild)}
          loading={hydrating && !hoveredChild}
        />
      </div>
    </div>
  )
}

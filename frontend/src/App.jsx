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
    openRelation,
    selectChild,
    back,
    reset,
    retry,
  } = useRegionStack()

  return (
    <div className="relative h-full w-full overflow-hidden">
      <RegionMap geojson={mapGeojson} />
      <NavPanel
        stack={stack}
        status={status}
        error={error}
        dropdown={dropdown}
        childrenCache={childrenCache}
        hydrating={hydrating}
        onOpenRelation={openRelation}
        onSelectChild={selectChild}
        onBack={back}
        onReset={reset}
        onRetry={retry}
      />
    </div>
  )
}

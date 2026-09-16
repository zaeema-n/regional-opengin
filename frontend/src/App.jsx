import NavPanel from './components/NavPanel.jsx'
import RegionMap from './components/RegionMap.jsx'

export default function App() {
  return (
    <div className="relative h-full w-full overflow-hidden">
      <RegionMap />
      <NavPanel />
    </div>
  )
}

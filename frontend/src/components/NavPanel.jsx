export default function NavPanel({ title = 'Region explorer' }) {
  return (
    <aside className="absolute top-4 left-4 z-[1000] flex max-h-[calc(100%-2rem)] w-80 flex-col overflow-auto rounded-lg bg-white/95 p-4 shadow-lg">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <p className="mt-2 text-sm text-slate-500">
        Choose a region type, then pick a name to zoom the map.
      </p>
    </aside>
  )
}

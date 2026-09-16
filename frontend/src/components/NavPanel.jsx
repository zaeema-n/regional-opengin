function childrenKey(parentId, relation) {
  return `${parentId}:${relation}`
}

function NavigationRow({
  fieldId,
  nav,
  items,
  selectedId,
  status,
  error,
  onOpen,
  onSelect,
}) {
  const showDropdown = Boolean(selectedId) || status !== 'idle'

  if (!showDropdown) {
    return (
      <button
        type="button"
        onClick={onOpen}
        className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-left text-sm font-medium text-slate-800 hover:border-blue-300 hover:bg-blue-50"
      >
        {nav.label}
      </button>
    )
  }

  return (
    <div>
      <label
        htmlFor={fieldId}
        className="text-xs font-semibold tracking-wide text-slate-500 uppercase"
      >
        {nav.label}
      </label>
      {status === 'loading' && (
        <p className="mt-1 text-sm text-slate-500">Loading…</p>
      )}
      {status === 'error' && (
        <div className="mt-1">
          <p className="text-sm text-red-600">{error}</p>
          <button
            type="button"
            onClick={onOpen}
            className="mt-1 text-sm font-medium text-blue-700 hover:text-blue-900"
          >
            Try again
          </button>
        </div>
      )}
      {status !== 'loading' && status !== 'error' && items.length === 0 && (
        <p className="mt-1 text-sm text-slate-500">No regions found.</p>
      )}
      {status !== 'loading' && items.length > 0 && (
        <select
          id={fieldId}
          className={`mt-1 w-full rounded-md border bg-white px-2 py-2 text-sm text-slate-900 ${
            selectedId ? 'border-blue-400' : 'border-slate-300'
          }`}
          value={selectedId ?? ''}
          onChange={(event) => onSelect(event.target.value)}
        >
          <option value="" disabled>
            Select {nav.label.toLowerCase()}
          </option>
          {items.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      )}
    </div>
  )
}

export default function NavPanel({
  stack,
  status,
  error,
  dropdown,
  childrenCache,
  hydrating,
  onOpenRelation,
  onSelectChild,
  onBack,
  onReset,
  onRetry,
}) {
  const rootName = stack[0]?.region?.name ?? 'Region explorer'
  const canNavigate = stack.length > 1

  return (
    <aside className="absolute top-4 left-4 z-[1000] flex max-h-[calc(100%-2rem)] w-80 flex-col overflow-auto rounded-lg bg-white/95 p-4 shadow-lg backdrop-blur-sm">
      <div className="flex items-start justify-between gap-2">
        <h1 className="text-lg font-semibold text-slate-900">
          {canNavigate ? (
            <button
              type="button"
              onClick={onReset}
              className="text-left hover:text-blue-700"
              title="Back to country"
            >
              {rootName}
            </button>
          ) : (
            rootName
          )}
        </h1>
        {canNavigate && (
          <button
            type="button"
            onClick={onBack}
            className="shrink-0 text-sm font-medium text-blue-700 hover:text-blue-900"
          >
            Back
          </button>
        )}
      </div>

      {status === 'loading' && (
        <p className="mt-2 text-sm text-slate-500">Loading regions…</p>
      )}

      {status === 'error' && (
        <div className="mt-2">
          <p className="text-sm text-red-600">{error}</p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-2 text-sm font-medium text-blue-700 hover:text-blue-900"
          >
            Try again
          </button>
        </div>
      )}

      {status === 'ready' && (
        <>
          <p className="mt-2 text-sm text-slate-500">
            Choose a region type, then pick a name to zoom the map.
          </p>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
          {stack.map((frame, index) => {
            const navigations = frame.region.navigations ?? []
            if (navigations.length === 0) {
              return null
            }
            const next = stack[index + 1]
            return (
              <section
                key={`${index}:${frame.region.id}`}
                className={
                  index === 0
                    ? 'mt-3 flex flex-col gap-2'
                    : 'mt-4 flex flex-col gap-2 border-t border-slate-200 pt-3'
                }
              >
                {navigations.map((nav) => {
                  const isSelectedPath = next?.relation === nav.relation
                  const isActive =
                    dropdown?.stackIndex === index &&
                    dropdown.relation === nav.relation
                  const items =
                    childrenCache[childrenKey(frame.region.id, nav.relation)] ??
                    []
                  let rowStatus = 'idle'
                  if (isActive) {
                    rowStatus = dropdown.status
                  } else if (isSelectedPath) {
                    rowStatus = 'ready'
                  }
                  return (
                    <NavigationRow
                      key={nav.relation}
                      fieldId={`region-${index}-${nav.relation}`}
                      nav={nav}
                      items={items}
                      selectedId={isSelectedPath ? next.region.id : ''}
                      status={rowStatus}
                      error={isActive ? dropdown.error : null}
                      onOpen={() => onOpenRelation(index, nav.relation)}
                      onSelect={(childId) =>
                        onSelectChild(index, nav.relation, childId)
                      }
                    />
                  )
                })}
              </section>
            )
          })}
          {hydrating && (
            <p className="mt-3 text-sm text-slate-500">Loading map…</p>
          )}
        </>
      )}
    </aside>
  )
}

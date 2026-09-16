function childrenKey(parentId, relation) {
  return `${parentId}:${relation}`
}

function NavigationRow({
  fieldId,
  nav,
  items,
  selectedId,
  hoveredId,
  status,
  error,
  onOpen,
  onSelect,
  onHover,
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
        <div
          id={fieldId}
          role="listbox"
          aria-label={nav.label}
          className={`mt-1 max-h-56 overflow-auto rounded-md border bg-white py-1 ${
            selectedId ? 'border-blue-400' : 'border-slate-300'
          }`}
          onMouseLeave={onHover ? () => onHover(null) : undefined}
          onBlur={
            onHover
              ? (event) => {
                  if (!event.currentTarget.contains(event.relatedTarget)) {
                    onHover(null)
                  }
                }
              : undefined
          }
        >
          {items.map((item) => {
            const selected = item.id === selectedId
            const hovered = Boolean(onHover) && item.id === hoveredId
            return (
              <button
                key={item.id}
                type="button"
                role="option"
                aria-selected={selected}
                className={`block w-full px-3 py-1.5 text-left text-sm ${
                  selected
                    ? 'bg-blue-100 font-medium text-blue-900'
                    : hovered
                      ? 'bg-blue-50 text-slate-900'
                      : 'text-slate-900 hover:bg-blue-50'
                }`}
                onMouseEnter={onHover ? () => onHover(item) : undefined}
                onFocus={onHover ? () => onHover(item) : undefined}
                onClick={() => {
                  if (item.id !== selectedId) {
                    onSelect(item.id)
                  }
                }}
              >
                {item.name}
              </button>
            )
          })}
        </div>
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
  hoveredChildId,
  onOpenRelation,
  onSelectChild,
  onHoverChild,
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
            Choose a region type, then hover a name to preview it on the map and click to zoom in.
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
                      hoveredId={isActive ? hoveredChildId : undefined}
                      status={rowStatus}
                      error={isActive ? dropdown.error : null}
                      onOpen={() => onOpenRelation(index, nav.relation)}
                      onSelect={(childId) =>
                        onSelectChild(index, nav.relation, childId)
                      }
                      onHover={isActive ? onHoverChild : undefined}
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

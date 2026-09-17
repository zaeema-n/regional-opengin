import { useEffect, useRef, useState } from 'react'

function childrenKey(parentId, relation) {
  return `${parentId}:${relation}`
}

function RegionPicker({
  fieldId,
  label,
  items,
  selectedId,
  selectedName,
  hoveredId,
  status,
  error,
  onOpen,
  onSelect,
  onHover,
  nested,
}) {
  const [editingId, setEditingId] = useState(null)
  const choosing = !selectedId || editingId === selectedId

  if (selectedId && !choosing) {
    return (
      <>
        <div className="mt-1.5 flex items-center justify-between gap-2 rounded-md border border-blue-400 bg-white px-3 py-2">
          <span className="text-sm font-medium text-blue-900">{selectedName}</span>
          <button
            type="button"
            onClick={() => {
              setEditingId(selectedId)
              onOpen()
            }}
            className="shrink-0 text-xs font-medium text-blue-700 hover:text-blue-900"
          >
            Change
          </button>
        </div>
        {nested}
      </>
    )
  }

  return (
    <>
      {selectedId && (
        <div className="mt-1 flex justify-end">
          <button
            type="button"
            onClick={() => setEditingId(null)}
            className="text-xs font-medium text-blue-700 hover:text-blue-900"
          >
            Done
          </button>
        </div>
      )}
      <RegionList
        fieldId={fieldId}
        label={label}
        items={items}
        selectedId={selectedId}
        hoveredId={hoveredId}
        status={status}
        error={error}
        onOpen={onOpen}
        onSelect={(childId) => {
          setEditingId(null)
          onSelect(childId)
        }}
        onHover={onHover}
      />
    </>
  )
}

function RegionList({
  fieldId,
  label,
  items,
  selectedId,
  hoveredId,
  status,
  error,
  onOpen,
  onSelect,
  onHover,
}) {
  const listRef = useRef(null)

  useEffect(() => {
    if (!hoveredId || !listRef.current) {
      return
    }
    const option = listRef.current.querySelector(
      `[data-region-id="${CSS.escape(hoveredId)}"]`,
    )
    option?.scrollIntoView({ block: 'nearest' })
  }, [hoveredId])

  if (status === 'loading') {
    return <p className="mt-1 text-sm text-slate-500">Loading…</p>
  }

  if (status === 'error') {
    return (
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
    )
  }

  if (items.length === 0) {
    return <p className="mt-1 text-sm text-slate-500">No regions found.</p>
  }

  return (
    <div
      ref={listRef}
      id={fieldId}
      role="listbox"
      aria-label={label}
      className={`mt-1.5 max-h-44 overflow-auto rounded-md border bg-white py-1 ${
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
            data-region-id={item.id}
            className={`flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-sm ${
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
            <span>{item.name}</span>
            {selected && (
              <span className="shrink-0 text-[10px] font-semibold tracking-wide text-blue-700 uppercase">
                Selected
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

function PathTrail({ stack, onGoTo }) {
  if (stack.length <= 1) {
    return null
  }

  return (
    <nav
      aria-label="Current path"
      className="mt-2 flex flex-wrap items-center gap-x-1 gap-y-0.5 text-xs text-slate-600"
    >
      {stack.map((frame, index) => {
        const isLast = index === stack.length - 1
        const via = frame.relation
          ? `via ${frame.relation.replaceAll('_', ' ')}`
          : 'country'
        return (
          <span key={`${index}:${frame.region.id}`} className="flex items-center gap-1">
            {index > 0 && (
              <span aria-hidden="true" className="text-slate-400">
                ›
              </span>
            )}
            {isLast ? (
              <span className="font-semibold text-slate-900" title={via}>
                {frame.region.name}
              </span>
            ) : (
              <button
                type="button"
                title={`Back to ${frame.region.name} (${via})`}
                onClick={() => onGoTo(index)}
                className="rounded-sm hover:text-blue-700 hover:underline"
              >
                {frame.region.name}
              </button>
            )}
          </span>
        )
      })}
    </nav>
  )
}

function LevelBlock({
  index,
  stack,
  dropdown,
  childrenCache,
  hoveredChildId,
  hydrating,
  onOpenRelation,
  onSelectChild,
  onHoverChild,
}) {
  const frame = stack[index]
  if (!frame) {
    return null
  }

  const navigations = frame.region.navigations ?? []
  if (navigations.length === 0) {
    if (hydrating && index === stack.length - 1) {
      return <p className="text-sm text-slate-500">Loading…</p>
    }
    return null
  }

  const next = stack[index + 1]
  const isFork = navigations.length > 1
  const previewRelation =
    dropdown?.stackIndex === index ? dropdown.relation : null

  return (
    <section
      className="flex flex-col gap-2"
      aria-label={
        isFork
          ? `Paths from ${frame.region.name}`
          : `Regions in ${frame.region.name}`
      }
    >
      {isFork && (
        <div>
          <p className="text-sm font-semibold text-slate-900">
            From {frame.region.name}
          </p>
          <p className="mt-0.5 text-xs leading-snug text-slate-500">
            Choose a navigation path.
          </p>
        </div>
      )}

      {navigations.map((nav, navIndex) => {
        const isSelectedPath = next?.relation === nav.relation
        const isActive = previewRelation === nav.relation
        const items =
          childrenCache[childrenKey(frame.region.id, nav.relation)] ?? []
        let rowStatus = 'idle'
        if (isActive) {
          rowStatus = dropdown.status
        } else if (isSelectedPath) {
          rowStatus = 'ready'
        }

        const showList = isSelectedPath || rowStatus !== 'idle'
        const previewingSibling = Boolean(previewRelation) && !isActive
        const showNested = isSelectedPath && !previewingSibling
        const listLabel = `${nav.label} in ${frame.region.name}`
        const selectedId = isSelectedPath ? next.region.id : ''

        const nested = showNested ? (
          <div className="mt-3 border-l-2 border-blue-400 pl-3">
            <LevelBlock
              index={index + 1}
              stack={stack}
              dropdown={dropdown}
              childrenCache={childrenCache}
              hoveredChildId={hoveredChildId}
              hydrating={hydrating}
              onOpenRelation={onOpenRelation}
              onSelectChild={onSelectChild}
              onHoverChild={onHoverChild}
            />
          </div>
        ) : null

        const picker = showList ? (
          <RegionPicker
            fieldId={`region-${index}-${nav.relation}`}
            label={listLabel}
            items={items}
            selectedId={selectedId}
            selectedName={isSelectedPath ? next.region.name : ''}
            hoveredId={isActive ? hoveredChildId : undefined}
            status={rowStatus}
            error={isActive ? dropdown.error : null}
            onOpen={() => onOpenRelation(index, nav.relation)}
            onSelect={(childId) =>
              onSelectChild(index, nav.relation, childId)
            }
            onHover={isActive ? onHoverChild : undefined}
            nested={nested}
          />
        ) : null

        if (!isFork) {
          return (
            <div key={nav.relation}>
              {showList ? (
                <>
                  <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
                    {nav.label}
                  </p>
                  <p className="text-xs text-slate-500">in {frame.region.name}</p>
                  {picker}
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => onOpenRelation(index, nav.relation)}
                  className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-left hover:border-blue-300 hover:bg-blue-50"
                >
                  <span className="block text-sm font-medium text-slate-800">
                    {nav.label}
                  </span>
                  <span className="mt-0.5 block text-xs text-slate-500">
                    in {frame.region.name}
                  </span>
                </button>
              )}
            </div>
          )
        }

        return (
          <div key={nav.relation}>
            {navIndex > 0 && (
              <p
                aria-hidden="true"
                className="my-1.5 text-center text-[11px] font-semibold tracking-widest text-slate-400 uppercase"
              >
                or
              </p>
            )}
            {showList ? (
              <div
                className={`rounded-md p-2.5 ${
                  isSelectedPath && !previewingSibling
                    ? 'border-2 border-blue-400 bg-blue-50/50'
                    : 'border border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {nav.label}
                    </p>
                    <p className="text-xs text-slate-500">
                      in {frame.region.name}
                    </p>
                  </div>
                  {isSelectedPath && !previewingSibling ? (
                    <span className="shrink-0 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-blue-800 uppercase">
                      This path
                    </span>
                  ) : next ? (
                    <span className="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-amber-800 uppercase">
                      Other path
                    </span>
                  ) : null}
                </div>
                {next && !isSelectedPath && (
                  <p className="mt-1 text-xs text-amber-800">
                    Selecting a region switches away from{' '}
                    {next.relation.replaceAll('_', ' ')}.
                  </p>
                )}
                {picker}
              </div>
            ) : (
              <button
                type="button"
                onClick={() => onOpenRelation(index, nav.relation)}
                className={
                  next
                    ? 'w-full rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2.5 text-left hover:border-blue-300 hover:bg-blue-50'
                    : 'w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-left hover:border-blue-300 hover:bg-blue-50'
                }
              >
                <span className="block text-sm font-semibold text-slate-800">
                  {nav.label}
                </span>
                <span className="mt-0.5 block text-xs text-slate-500">
                  {next
                    ? `Other path · in ${frame.region.name}`
                    : `in ${frame.region.name}`}
                </span>
              </button>
            )}
          </div>
        )
      })}
    </section>
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
  onGoTo,
  onRetry,
}) {
  const rootName = stack[0]?.region?.name ?? 'Region explorer'
  const canNavigate = stack.length > 1

  return (
    <aside className="flex min-h-0 flex-col overflow-auto rounded-lg bg-white/50 p-4 shadow-lg backdrop-blur-md">
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

      <PathTrail stack={stack} onGoTo={onGoTo} />

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
          <p className="mt-2 text-xs text-slate-500">
            Hover over a name or a map region to preview it, then click to zoom in.
          </p>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
          <div className="mt-3">
            <LevelBlock
              index={0}
              stack={stack}
              dropdown={dropdown}
              childrenCache={childrenCache}
              hoveredChildId={hoveredChildId}
              hydrating={hydrating}
              onOpenRelation={onOpenRelation}
              onSelectChild={onSelectChild}
              onHoverChild={onHoverChild}
            />
          </div>
          {hydrating && (
            <p className="mt-3 text-sm text-slate-500">Loading map…</p>
          )}
        </>
      )}
    </aside>
  )
}

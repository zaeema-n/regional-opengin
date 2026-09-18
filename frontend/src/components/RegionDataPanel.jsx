function formatHeader(name) {
  const label = String(name).replaceAll('_', ' ').replaceAll('/', ' / ').trim()
  return label.replace(/\b\w/g, (char) => char.toUpperCase())
}

function columnKey(name) {
  return String(name)
    .trim()
    .toLowerCase()
    .replaceAll(/[\s_-]+/g, '')
}

function isHiddenColumn(name) {
  const key = columnKey(name)
  return key === 'id' || key === 'entityid' || key === 'date'
}

function isTotalColumn(name) {
  return columnKey(name).startsWith('total')
}

function visibleColumns(columns) {
  return columns
    .map((column, index) => ({ column, index }))
    .filter(({ column }) => !isHiddenColumn(column))
}

function numericValue(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
      const n = Number(trimmed)
      return Number.isFinite(n) ? n : null
    }
  }
  return null
}

function formatCount(value) {
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: Number.isInteger(value) ? 0 : 2,
  }).format(value)
}

function formatPercent(value) {
  const formatted = (digits) =>
    new Intl.NumberFormat('en-US', {
      maximumFractionDigits: digits,
    }).format(value)

  let text = formatted(1)
  if (value > 0 && Number(text) === 0) {
    text = formatted(3)
  }
  if (value > 0 && Number(text) === 0) {
    return '<0.001%'
  }
  return `${text}%`
}

const SLICE_COLORS = [
  '#2563eb',
  '#f59e0b',
  '#10b981',
  '#8b5cf6',
  '#ef4444',
  '#06b6d4',
  '#f97316',
  '#84cc16',
  '#ec4899',
  '#64748b',
]

function categorySlices(columns, row) {
  const items = []
  for (const { column, index } of visibleColumns(columns)) {
    if (isTotalColumn(column)) {
      continue
    }
    const n = numericValue(row[index])
    if (n == null || n <= 0) {
      continue
    }
    items.push({
      key: column,
      label: formatHeader(column),
      value: n,
    })
  }
  items.sort((a, b) => b.value - a.value)
  const total = items.reduce((sum, item) => sum + item.value, 0)
  return items.map((item, index) => ({
    ...item,
    color: SLICE_COLORS[index % SLICE_COLORS.length],
    percent: total > 0 ? (item.value / total) * 100 : 0,
  }))
}

function pointOnCircle(cx, cy, radius, angleDeg) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180
  return [cx + radius * Math.cos(angleRad), cy + radius * Math.sin(angleRad)]
}

function slicePath(cx, cy, radius, startAngle, endAngle) {
  const [x1, y1] = pointOnCircle(cx, cy, radius, startAngle)
  const [x2, y2] = pointOnCircle(cx, cy, radius, endAngle)
  const largeArc = endAngle - startAngle > 180 ? 1 : 0
  return `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`
}

function pieArcs(slices) {
  return slices.reduce((arcs, slice, index) => {
    const startAngle = arcs.at(-1)?.endAngle ?? 0
    const sweep = (slice.percent / 100) * 360
    const endAngle = index === slices.length - 1 ? 360 : startAngle + sweep
    return [...arcs, { ...slice, startAngle, endAngle }]
  }, [])
}

function PieChart({ slices, label }) {
  const cx = 60
  const cy = 60
  const radius = 56
  const arcs = pieArcs(slices)
  const summary = slices
    .map((slice) => `${slice.label} ${formatPercent(slice.percent)}`)
    .join(', ')

  return (
    <svg
      viewBox="0 0 120 120"
      className="size-28 shrink-0"
      role="img"
      aria-label={`${label}: ${summary}`}
    >
      {arcs.length === 1 ? (
        <circle cx={cx} cy={cy} r={radius} fill={arcs[0].color} />
      ) : (
        arcs.map((arc) => (
          <path
            key={arc.key}
            d={slicePath(cx, cy, radius, arc.startAngle, arc.endAngle)}
            fill={arc.color}
            stroke="white"
            strokeWidth="1"
          />
        ))
      )}
    </svg>
  )
}

function DatasetChart({ dataset }) {
  const rows = dataset.rows ?? []
  const charts = rows
    .map((row, rowIndex) => ({
      rowIndex,
      slices: categorySlices(dataset.columns ?? [], row),
    }))
    .filter((chart) => chart.slices.length > 0)

  return (
    <section>
      <h3 className="text-sm font-semibold text-slate-900">{dataset.name}</h3>
      {charts.length === 0 ? (
        <p className="mt-1 text-sm text-slate-500">No rows for this dataset.</p>
      ) : (
        <div className="mt-2 flex flex-col gap-3">
          {charts.map((chart) => (
            <div
              key={chart.rowIndex}
              className="flex items-start gap-3"
            >
              <ul className="min-w-0 flex-1">
                {chart.slices.map((slice) => (
                  <li
                    key={slice.key}
                    className="flex items-start gap-2 py-1"
                  >
                    <span
                      className="mt-1 size-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: slice.color }}
                      aria-hidden="true"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="truncate text-xs font-medium text-slate-800">
                          {slice.label}
                        </span>
                        <span className="shrink-0 text-xs font-semibold text-slate-900 tabular-nums">
                          {formatPercent(slice.percent)}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 tabular-nums">
                        {formatCount(slice.value)}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
              <PieChart slices={chart.slices} label={dataset.name} />
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default function RegionDataPanel({
  region,
  status,
  error,
  datasets,
  onLoad,
}) {
  if (!region) {
    return null
  }

  const tables = datasets ?? []

  return (
    <aside
      className="shrink-0 rounded-lg bg-white/50 p-4 shadow-lg backdrop-blur-md"
      aria-label={`Data for ${region.name}`}
      aria-busy={status === 'loading'}
    >
      <h2 className="text-sm font-semibold text-slate-900">{region.name}</h2>

      {status === 'idle' && (
        <button
          type="button"
          onClick={onLoad}
          className="mt-3 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-left hover:border-blue-300 hover:bg-blue-50"
        >
          <span className="block text-sm font-medium text-slate-800">
            Show data
          </span>
        </button>
      )}

      {status === 'loading' && (
        <p className="mt-3 text-sm text-slate-500">Loading data…</p>
      )}

      {status === 'error' && (
        <div className="mt-3">
          <p className="text-sm text-red-600">
            {error || 'Failed to load data'}
          </p>
          <button
            type="button"
            onClick={onLoad}
            className="mt-2 text-sm font-medium text-blue-700 hover:text-blue-900"
          >
            Try again
          </button>
        </div>
      )}

      {status === 'ready' && tables.length === 0 && (
        <p className="mt-3 text-sm text-slate-500">
          No data available for {region.name}.
        </p>
      )}

      {status === 'ready' && tables.length > 0 && (
        <div className="mt-3 flex flex-col gap-5">
          {tables.map((dataset) => (
            <DatasetChart key={dataset.id} dataset={dataset} />
          ))}
        </div>
      )}
    </aside>
  )
}

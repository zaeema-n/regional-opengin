function formatHeader(name) {
  return String(name).replaceAll('_', ' ')
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

function formatCell(value) {
  if (value == null || value === '') {
    return '—'
  }
  const n = numericValue(value)
  if (n != null) {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: Number.isInteger(n) ? 0 : 2,
    }).format(n)
  }
  return String(value)
}

function DatasetTable({ dataset }) {
  const columns = dataset.columns ?? []
  const rows = dataset.rows ?? []

  return (
    <section>
      <h3 className="text-sm font-semibold text-slate-900">{dataset.name}</h3>
      {columns.length === 0 || rows.length === 0 ? (
        <p className="mt-1 text-sm text-slate-500">No rows for this dataset.</p>
      ) : (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-max border-collapse text-left text-xs">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th
                    key={column}
                    className="border-b border-slate-200 px-2 py-1 font-semibold tracking-wide text-slate-500 uppercase"
                  >
                    {formatHeader(column)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {columns.map((column, columnIndex) => {
                    const value = row[columnIndex]
                    const numeric = numericValue(value) != null
                    return (
                      <td
                        key={`${rowIndex}:${column}`}
                        className={`border-b border-slate-100 px-2 py-1 text-slate-900 tabular-nums ${
                          numeric ? 'text-right' : ''
                        }`}
                      >
                        {formatCell(value)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
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
      {status === 'idle' && (
        <button
          type="button"
          onClick={onLoad}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-left hover:border-blue-300 hover:bg-blue-50"
        >
          <span className="block text-sm font-medium text-slate-800">
            Show data for {region.name}
          </span>
        </button>
      )}

      {status === 'loading' && (
        <p className="text-sm text-slate-500">Loading data…</p>
      )}

      {status === 'error' && (
        <div>
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
        <p className="text-sm text-slate-500">
          No data available for {region.name}.
        </p>
      )}

      {status === 'ready' && tables.length > 0 && (
        <div className="flex flex-col gap-4">
          {tables.map((dataset) => (
            <DatasetTable key={dataset.id} dataset={dataset} />
          ))}
        </div>
      )}
    </aside>
  )
}

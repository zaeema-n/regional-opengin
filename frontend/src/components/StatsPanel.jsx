function featureProperties(geojson) {
  if (!geojson || typeof geojson !== 'object') {
    return null
  }
  if (geojson.type === 'FeatureCollection') {
    const feature = Array.isArray(geojson.features)
      ? geojson.features.find(Boolean)
      : null
    return feature?.properties ?? null
  }
  if (geojson.type === 'Feature') {
    return geojson.properties ?? null
  }
  return null
}

function numericValue(value) {
  if (value == null || value === '') {
    return null
  }
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function formatPopulation(value) {
  return new Intl.NumberFormat('en-US').format(value)
}

function formatArea(value) {
  return `${new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
  }).format(value)} km²`
}

function kindLabel(kind) {
  const minor = kind?.minor
  if (!minor) {
    return null
  }
  const slug = minor.includes('+')
    ? minor.slice(minor.lastIndexOf('+') + 1)
    : minor
  const label = slug
    .replace(/^lk-/, '')
    .replaceAll('-', ' ')
    .replaceAll('_', ' ')
    .trim()
  if (!label) {
    return null
  }
  return label.replace(/\b\w/g, (char) => char.toUpperCase())
}

function StatRow({ label, value }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
        {label}
      </dt>
      <dd className="text-sm font-semibold text-slate-900 tabular-nums">
        {value}
      </dd>
    </div>
  )
}

export default function StatsPanel({ region, preview, loading }) {
  if (!region) {
    return null
  }

  const props = featureProperties(region.geojson)
  const population = numericValue(props?.population)
  const area = numericValue(props?.area)
  const typeLabel = kindLabel(region.kind)
  const hasStats = population != null || area != null

  return (
    <aside
      className="shrink-0 rounded-lg bg-white/50 p-4 shadow-lg backdrop-blur-md"
      aria-label={`Population and area for ${region.name}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{region.name}</h2>
          {typeLabel && (
            <p className="mt-0.5 text-xs text-slate-500">{typeLabel}</p>
          )}
        </div>
        {preview && (
          <span className="shrink-0 rounded-full bg-orange-50 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-orange-800 uppercase">
            Preview
          </span>
        )}
      </div>

      {loading && !hasStats ? (
        <p className="mt-3 text-sm text-slate-500">Loading…</p>
      ) : hasStats ? (
        <dl className="mt-3 flex flex-col gap-2">
          {population != null && (
            <StatRow label="Population" value={formatPopulation(population)} />
          )}
          {area != null && (
            <StatRow label="Area" value={formatArea(area)} />
          )}
        </dl>
      ) : (
        <p className="mt-3 text-sm text-slate-500">
          No population or area data.
        </p>
      )}
    </aside>
  )
}

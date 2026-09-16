const BASE = '/v1/regions'

async function getJson(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

export function getRootRegion() {
  return getJson(`${BASE}/root`)
}

export function getRegion(id) {
  return getJson(`${BASE}/${encodeURIComponent(id)}`)
}

export function getRegionChildren(id, relation, includeGeojson = false) {
  const params = new URLSearchParams({ relation })
  if (includeGeojson) {
    params.set('include_geojson', 'true')
  }
  return getJson(`${BASE}/${encodeURIComponent(id)}/children?${params}`)
}

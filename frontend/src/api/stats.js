const BASE = '/v1/regions'

async function getJson(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

export function getRegionStats(regionId) {
  return getJson(`${BASE}/${encodeURIComponent(regionId)}/stats`)
}

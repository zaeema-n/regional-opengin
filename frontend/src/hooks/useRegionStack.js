import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getRegion, getRegionChildren, getRootRegion } from '../api/regions.js'

function childrenKey(parentId, relation) {
  return `${parentId}:${relation}`
}

function sortByName(items) {
  return [...items].sort((a, b) => a.name.localeCompare(b.name, 'en'))
}

export function hasRenderableGeometry(geojson) {
  if (!geojson || typeof geojson !== 'object') {
    return false
  }
  if (geojson.type === 'FeatureCollection') {
    return Array.isArray(geojson.features) && geojson.features.length > 0
  }
  if (geojson.type === 'Feature') {
    return Boolean(geojson.geometry)
  }
  return false
}

function placeholderRegion(child) {
  return {
    id: child.id,
    name: child.name,
    kind: child.kind,
    geojson: null,
    navigations: [],
  }
}

export function useRegionStack() {
  const [stack, setStack] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [dropdown, setDropdown] = useState(null)
  const [childrenCache, setChildrenCache] = useState({})
  const [hydrating, setHydrating] = useState(false)

  const stackRef = useRef(stack)
  const cacheRef = useRef(childrenCache)
  const opGen = useRef(0)
  const childrenGen = useRef(0)

  useEffect(() => {
    stackRef.current = stack
    cacheRef.current = childrenCache
  }, [stack, childrenCache])

  const loadRoot = useCallback(() => {
    const gen = ++opGen.current
    setStatus('loading')
    setError(null)
    setHydrating(false)
    setDropdown(null)
    setStack([])

    getRootRegion()
      .then((region) => {
        if (gen !== opGen.current) {
          return
        }
        setStack([{ region, relation: null }])
        setStatus('ready')
      })
      .catch((err) => {
        if (gen !== opGen.current) {
          return
        }
        setError(err.message || 'Failed to load regions')
        setStatus('error')
      })
  }, [])

  useEffect(() => {
    const gen = ++opGen.current
    getRootRegion()
      .then((region) => {
        if (gen !== opGen.current) {
          return
        }
        setStack([{ region, relation: null }])
        setStatus('ready')
      })
      .catch((err) => {
        if (gen !== opGen.current) {
          return
        }
        setError(err.message || 'Failed to load regions')
        setStatus('error')
      })
  }, [])

  const openRelation = useCallback(async (stackIndex, relation) => {
    const parent = stackRef.current[stackIndex]
    if (!parent) {
      return
    }

    const key = childrenKey(parent.region.id, relation)
    const cached = cacheRef.current[key]
    if (cached) {
      setDropdown({ stackIndex, relation, status: 'ready', error: null })
      return
    }

    const gen = ++childrenGen.current
    setDropdown({ stackIndex, relation, status: 'loading', error: null })

    try {
      const data = await getRegionChildren(parent.region.id, relation)
      const items = sortByName(data.items ?? [])
      if (gen !== childrenGen.current) {
        return
      }
      setChildrenCache((prev) => {
        const next = { ...prev, [key]: items }
        cacheRef.current = next
        return next
      })
      setDropdown({ stackIndex, relation, status: 'ready', error: null })
    } catch (err) {
      if (gen !== childrenGen.current) {
        return
      }
      setDropdown({
        stackIndex,
        relation,
        status: 'error',
        error: err.message || 'Failed to load regions',
      })
    }
  }, [])

  const selectChild = useCallback(async (stackIndex, relation, childId) => {
    const parent = stackRef.current[stackIndex]
    if (!parent || !childId) {
      return
    }

    const key = childrenKey(parent.region.id, relation)
    const child = (cacheRef.current[key] ?? []).find((item) => item.id === childId)
    if (!child) {
      return
    }

    const gen = ++opGen.current
    setError(null)
    setDropdown(null)
    setHydrating(true)
    setStack((prev) => {
      const next = [
        ...prev.slice(0, stackIndex + 1),
        { region: placeholderRegion(child), relation },
      ]
      stackRef.current = next
      return next
    })

    try {
      const region = await getRegion(childId)
      if (gen !== opGen.current) {
        return
      }
      setStack((prev) => [
        ...prev.slice(0, stackIndex + 1),
        { region, relation },
      ])
    } catch (err) {
      if (gen !== opGen.current) {
        return
      }
      setError(err.message || 'Failed to load region')
      setStack((prev) => prev.slice(0, stackIndex + 1))
      setDropdown({ stackIndex, relation, status: 'ready', error: null })
    } finally {
      if (gen === opGen.current) {
        setHydrating(false)
      }
    }
  }, [])

  const back = useCallback(() => {
    const frames = stackRef.current
    if (frames.length <= 1) {
      return
    }
    const parentIndex = frames.length - 2
    const parent = frames[parentIndex]
    const removed = frames[frames.length - 1]
    opGen.current += 1
    setHydrating(false)
    setError(null)
    setStack(frames.slice(0, -1))
    const key = childrenKey(parent.region.id, removed.relation)
    if (cacheRef.current[key]) {
      setDropdown({
        stackIndex: parentIndex,
        relation: removed.relation,
        status: 'ready',
        error: null,
      })
    } else {
      setDropdown(null)
    }
  }, [])

  const reset = useCallback(() => {
    if (stackRef.current.length <= 1) {
      return
    }
    opGen.current += 1
    setHydrating(false)
    setError(null)
    setDropdown(null)
    setStack((prev) => prev.slice(0, 1))
  }, [])

  const selectedRegion = stack.at(-1)?.region ?? null

  const mapGeojson = useMemo(() => {
    for (let index = stack.length - 1; index >= 0; index -= 1) {
      const geojson = stack[index].region.geojson
      if (hasRenderableGeometry(geojson)) {
        return geojson
      }
    }
    return null
  }, [stack])

  return {
    stack,
    status,
    error,
    dropdown,
    childrenCache,
    hydrating,
    selectedRegion,
    mapGeojson,
    openRelation,
    selectChild,
    back,
    reset,
    retry: loadRoot,
  }
}

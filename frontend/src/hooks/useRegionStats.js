import { useCallback, useRef, useState } from 'react'
import { getRegionStats } from '../api/stats.js'

export function useRegionStats(regionId) {
  const [state, setState] = useState({
    regionId,
    status: 'idle',
    error: null,
    data: null,
  })
  const genRef = useRef(0)

  if (state.regionId !== regionId) {
    setState({
      regionId,
      status: 'idle',
      error: null,
      data: null,
    })
  }

  const load = useCallback(() => {
    if (!regionId) {
      return
    }

    const requestedId = regionId
    const gen = ++genRef.current
    setState({
      regionId: requestedId,
      status: 'loading',
      error: null,
      data: null,
    })

    getRegionStats(requestedId)
      .then((result) => {
        if (gen !== genRef.current) {
          return
        }
        setState((prev) => {
          if (prev.regionId !== requestedId) {
            return prev
          }
          return { ...prev, status: 'ready', data: result, error: null }
        })
      })
      .catch((err) => {
        if (gen !== genRef.current) {
          return
        }
        setState((prev) => {
          if (prev.regionId !== requestedId) {
            return prev
          }
          return {
            ...prev,
            status: 'error',
            error: err.message || 'Failed to load data',
            data: null,
          }
        })
      })
  }, [regionId])

  const visible =
    state.regionId === regionId
      ? state
      : { status: 'idle', error: null, data: null }

  return {
    status: visible.status,
    error: visible.error,
    data: visible.data,
    load,
  }
}

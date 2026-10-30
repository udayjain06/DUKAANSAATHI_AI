import { useState, useCallback } from 'react'
import api from '../api'

export function useApi(url, options = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetch = useCallback(async (params) => {
    setLoading(true)
    setError(null)
    try {
      const res = options.method === 'post'
        ? await api.post(url, params)
        : await api.get(url, { params })
      setData(res.data)
      return res.data
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Request failed'
      setError(msg)
      throw e
    } finally {
      setLoading(false)
    }
  }, [url, options.method])

  return { data, loading, error, fetch, setData }
}


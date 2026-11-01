import { useCallback, useEffect, useState } from 'react'
import { mockApi } from '../services/mockApi.js'

export function useDemoData() {
  const [orders, setOrders] = useState([])
  const [quote, setQuote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [orderData, quoteData] = await Promise.all([mockApi.listOrders(), mockApi.getQuote()])
      setOrders(orderData)
      setQuote(quoteData)
      setError('')
    } catch {
      setError('Your demo data could not be loaded. Refresh the page to try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh() }, 0)
    return () => window.clearTimeout(timer)
  }, [refresh])

  useEffect(() => {
    if (!notice) return undefined
    const timer = window.setTimeout(() => setNotice(''), 3600)
    return () => window.clearTimeout(timer)
  }, [notice])

  const mutate = async (action, success) => {
    setError('')
    try {
      await action()
      await refresh()
      setNotice(success)
    } catch (caught) {
      setError(caught.message || 'Something went wrong. Please try again.')
    }
  }

  const dismiss = () => {
    setError('')
    setNotice('')
  }

  return { orders, quote, loading, notice, error, refresh, mutate, dismiss }
}

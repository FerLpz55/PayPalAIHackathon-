import { useCallback, useEffect, useState } from 'react'
import { apiClient, isDemoMode, isConnectedMode, isConfigurationMissing, getSession } from '../services/apiClient.js'

export function useDemoData({ customerMode = false, enabled = true } = {}) {
  const [orders, setOrders] = useState([])
  const [quote, setQuote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    if (!enabled) {
      setOrders([])
      setQuote(null)
      setError('')
      setLoading(false)
      return
    }
    setLoading(true)
    if (isConfigurationMissing) {
      setOrders([])
      setQuote(null)
      setError('Backend connection is not configured. Set VITE_API_BASE_URL, or explicitly select VITE_APP_MODE=demo to view sample data.')
      setLoading(false)
      return
    }
    try {
      let quoteData
      let orderData
      if (customerMode && isConnectedMode && getSession().customerToken) {
        // Un enlace de cliente recupera la cotización, el pedido y los pagos
        // con el token; nunca se adivinan recursos por ID.
        const context = await apiClient.getCustomerContext()
        quoteData = context?.quote || null
        orderData = context?.order || null
      } else {
        quoteData = await apiClient.getQuote()
        orderData = customerMode && quoteData && apiClient.getCustomerOrder
          ? await apiClient.getCustomerOrder(quoteData.numericId || quoteData.id)
          : customerMode
            ? null
            : await apiClient.listOrders()
      }
      setOrders(Array.isArray(orderData) ? orderData : orderData ? [orderData] : customerMode && isDemoMode ? await apiClient.listOrders() : [])
      setQuote(quoteData)
      setError('')
    } catch (caught) {
      setError(caught?.message || 'Your data could not be loaded. Refresh the page to try again.')
    } finally {
      setLoading(false)
    }
  }, [customerMode, enabled])

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

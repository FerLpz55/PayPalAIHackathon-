import { useCallback, useEffect, useRef, useState } from 'react'
import { apiClient, getSession, isConnectedMode, isDemoMode, isConfigurationMissing } from '../services/apiClient.js'

function sessionScopeFingerprint(token) {
  if (!token) return 'anonymous'
  let hash = 2166136261
  for (let index = 0; index < token.length; index += 1) {
    hash = Math.imul(hash ^ token.charCodeAt(index), 16777619)
  }
  return (hash >>> 0).toString(36)
}

export function useDemoData({ customerMode = false, quoteId = null, enabled = true } = {}) {
  const customerSession = customerMode ? getSession() : null
  const scope = customerMode
    ? `customer:${String(quoteId ?? customerSession.activeQuoteId ?? 'active')}:${sessionScopeFingerprint(customerSession.customerToken)}`
    : 'workshop'
  const [ordersRecord, setOrdersRecord] = useState({ scope, value: [] })
  const [quoteRecord, setQuoteRecord] = useState({ scope, value: null })
  const [loadingRecord, setLoadingRecord] = useState({ scope, value: true })
  const [noticeRecord, setNoticeRecord] = useState({ scope, value: '' })
  const [errorRecord, setErrorRecord] = useState({ scope, value: '' })
  const requestSequence = useRef(0)
  const orders = enabled && ordersRecord.scope === scope ? ordersRecord.value : []
  const quote = enabled && quoteRecord.scope === scope ? quoteRecord.value : null
  const loading = enabled && loadingRecord.scope === scope ? loadingRecord.value : enabled
  const notice = enabled && noticeRecord.scope === scope ? noticeRecord.value : ''
  const error = enabled && errorRecord.scope === scope ? errorRecord.value : ''

  const refresh = useCallback(async () => {
    const requestId = ++requestSequence.current
    const isCurrentRequest = () => requestId === requestSequence.current
    if (!enabled) return
    setLoadingRecord({ scope, value: true })
    if (isConfigurationMissing) {
      setOrdersRecord({ scope, value: [] })
      setQuoteRecord({ scope, value: null })
      setErrorRecord({ scope, value: 'Backend connection is not configured. Set VITE_API_BASE_URL, or explicitly select VITE_APP_MODE=demo to view sample data.' })
      setLoadingRecord({ scope, value: false })
      return
    }
    try {
      let quoteData
      let orderData
      if (customerMode && isConnectedMode && getSession().customerToken) {
        // El enlace seguro recupera todo el contexto por token; nunca adivina
        // recursos por el ID que pueda quedar en la URL.
        const context = await apiClient.getCustomerContext()
        quoteData = context?.quote || null
        orderData = context?.order || null
      } else {
        quoteData = await apiClient.getQuote(quoteId)
        orderData = customerMode && quoteData && apiClient.getCustomerOrder
          ? await apiClient.getCustomerOrder(quoteData.numericId || quoteData.id)
          : customerMode
            ? null
            : await apiClient.listOrders()
      }
      const resolvedOrders = Array.isArray(orderData) ? orderData : orderData ? [orderData] : customerMode && isDemoMode ? await apiClient.listOrders() : []
      if (!isCurrentRequest()) return
      setOrdersRecord({ scope, value: resolvedOrders })
      setQuoteRecord({ scope, value: quoteData })
      setErrorRecord({ scope, value: '' })
    } catch (caught) {
      if (isCurrentRequest()) {
        if (caught?.status === 401 || caught?.status === 403) {
          setOrdersRecord({ scope, value: [] })
          setQuoteRecord({ scope, value: null })
        }
        setErrorRecord({ scope, value: caught?.message || 'Your data could not be loaded. Refresh the page to try again.' })
      }
    } finally {
      if (isCurrentRequest()) setLoadingRecord({ scope, value: false })
    }
  }, [customerMode, quoteId, scope, enabled])

  useEffect(() => {
    if (!enabled) return undefined
    const timer = window.setTimeout(() => { void refresh() }, 0)
    return () => window.clearTimeout(timer)
  }, [refresh, enabled])

  useEffect(() => {
    if (!notice) return undefined
    const timer = window.setTimeout(() => {
      setNoticeRecord((current) => current.scope === scope ? { ...current, value: '' } : current)
    }, 3600)
    return () => window.clearTimeout(timer)
  }, [notice, scope])

  const mutate = async (action, success) => {
    setErrorRecord({ scope, value: '' })
    try {
      const result = await action()
      await refresh()
      setNoticeRecord({ scope, value: success })
      return result ?? true
    } catch (caught) {
      setErrorRecord({ scope, value: caught.message || 'Something went wrong. Please try again.' })
      return false
    }
  }

  const dismiss = () => {
    setErrorRecord({ scope, value: '' })
    setNoticeRecord({ scope, value: '' })
  }

  return { orders, quote, loading, notice, error, refresh, mutate, dismiss }
}

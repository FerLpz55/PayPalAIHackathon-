import { useCallback, useEffect, useState } from 'react'
import { trackPageView } from '../utils/analytics.js'

const ROUTE_TITLES = {
  dashboard: 'Dashboard · Workshop Overview',
  orders: 'Orders · Status Pipeline',
  quotes: 'Quotes · Estimate Pipeline',
  receipts: 'Material Receipts · Expenses',
  accounting: 'Accounting · Financial Overview',
  'customer/new': 'Request a Custom Woodwork Estimate',
  'customer/quote': 'Your Project Estimate · Review',
  'customer/tracking': 'Order Tracking & Payments',
  'customer/payment/return': 'Verifying PayPal Payment',
  'customer/payment/cancel': 'PayPal Payment Cancelled',
}

function readLocation() {
  const [path = '', query = ''] = window.location.hash.replace(/^#\/?/, '').split('?')
  return { route: path || 'customer/new', query }
}

function titleForRoute(route) {
  if (ROUTE_TITLES[route]) return ROUTE_TITLES[route]
  if (route.startsWith('order/')) return `Order ${route.split('/')[1] || ''} · Details`
  return 'Carpentry Orders'
}

export function useHashRoute(onRouteChange) {
  const [location, setLocation] = useState(readLocation)
  const { route, query } = location

  useEffect(() => {
    const handleHashChange = () => {
      const nextLocation = readLocation()
      setLocation(nextLocation)
      document.title = `${titleForRoute(nextLocation.route)} · TallerClaro`
      trackPageView(nextLocation.route)
      onRouteChange?.()
    }

    handleHashChange()
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [onRouteChange])

  const go = useCallback((target) => {
    const next = target.replace(/^#\/?/, '')
    window.location.hash = `#/${next}`
  }, [])

  return { route, query, go }
}

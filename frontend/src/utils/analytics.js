/**
 * Despachador desacoplado de telemetría y eventos analíticos de frontend.
 */

export function trackEvent(eventName, payload = {}) {
  if (typeof window === 'undefined') return
  if (window.dataLayer && Array.isArray(window.dataLayer)) {
    window.dataLayer.push({ event: eventName, ...payload, timestamp: new Date().toISOString() })
  }
}

export function trackPageView(route) {
  trackEvent('page_view', { page_path: `/#/${route}` })
}

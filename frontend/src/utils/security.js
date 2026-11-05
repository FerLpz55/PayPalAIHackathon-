/**
 * Utilidades de seguridad para validación de URLs y sanitización de parámetros.
 */

const ALLOWED_PAYPAL_HOSTS = new Set([
  'sandbox.paypal.com',
  'www.sandbox.paypal.com',
  'paypal.com',
  'www.paypal.com',
])

/**
 * Valida que una URL pertenezca legítimamente a PayPal sobre protocolo HTTPS.
 * Rechaza esquemas javascript:, data:, hosts no autorizados o ataques de subdominio.
 *
 * @param {string|null|undefined} rawUrl
 * @returns {boolean}
 */
export function isSafePayPalUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') return false
  try {
    const parsed = new URL(rawUrl)
    if (parsed.protocol !== 'https:') return false
    return ALLOWED_PAYPAL_HOSTS.has(parsed.hostname.toLowerCase())
  } catch {
    return false
  }
}

/**
 * Elimina tokens y datos sensibles de PayPal de la URL actual sin recargar la página.
 */
export function cleanPayPalUrlParams() {
  if (typeof window === 'undefined' || !window.location) return
  const search = new URLSearchParams(window.location.search)
  search.delete('token')
  search.delete('PayerID')

  const hashParts = (window.location.hash || '').split('?')
  const hashPath = hashParts[0] || ''
  const hashParams = new URLSearchParams(hashParts.slice(1).join('?'))
  hashParams.delete('token')
  hashParams.delete('PayerID')

  const remainingSearch = search.toString()
  const remainingHashParams = hashParams.toString()
  const cleanUrl = `${window.location.pathname}${remainingSearch ? `?${remainingSearch}` : ''}${hashPath}${remainingHashParams ? `?${remainingHashParams}` : ''}`
  window.history.replaceState(window.history.state, '', cleanUrl)
}

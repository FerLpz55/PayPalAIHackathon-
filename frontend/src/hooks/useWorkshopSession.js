import { useCallback, useEffect, useState } from 'react'
import {
  apiClient,
  isConfigurationMissing,
  isDemoMode,
} from '../services/apiClient.js'
import { SESSION_EXPIRED_EVENT } from '../services/http.js'

/**
 * Estado de la sesión del taller.
 *
 * `checking` mientras se consulta la cookie, `anonymous` si no hay sesión,
 * `authenticated` tras el login y `error` si el backend no responde. El hook
 * no inventa una sesión local: la cookie HttpOnly es la única autoridad.
 */
export function useWorkshopSession({ enabled = true } = {}) {
  const [status, setStatus] = useState(() => {
    if (!enabled) return 'idle'
    if (isDemoMode) return 'authenticated'
    if (isConfigurationMissing) return 'unconfigured'
    return 'checking'
  })
  const [workshopSession, setWorkshopSession] = useState(null)
  const [error, setError] = useState('')

  const check = useCallback(async () => {
    if (!enabled) return null
    if (isDemoMode) {
      setStatus('authenticated')
      return { authenticated: true, username: 'demo', demo: true }
    }
    if (isConfigurationMissing) {
      setStatus('unconfigured')
      return null
    }
    setStatus('checking')
    try {
      const session = await apiClient.getWorkshopSession()
      if (session) {
        setWorkshopSession(session)
        setStatus('authenticated')
        setError('')
      } else {
        setWorkshopSession(null)
        setStatus('anonymous')
      }
      return session
    } catch (caught) {
      setWorkshopSession(null)
      setStatus('error')
      setError(caught?.message || 'The workshop session could not be checked.')
      return null
    }
  }, [enabled])

  useEffect(() => {
    // Se difiere un microtask para no encadenar renders desde el cuerpo del
    // efecto; el estado inicial ya muestra "checking".
    const timer = Promise.resolve().then(check)
    return () => { void timer }
  }, [check])

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return undefined
    const handleExpired = () => {
      setWorkshopSession(null)
      setStatus('anonymous')
      setError('Your workshop session expired. Sign in again to continue.')
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, handleExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleExpired)
  }, [enabled])

  const login = useCallback(async (username, password) => {
    setError('')
    const session = await apiClient.loginWorkshop(username, password)
    setWorkshopSession(session)
    setStatus('authenticated')
    return session
  }, [])

  const logout = useCallback(async () => {
    setStatus('signing_out')
    try {
      await apiClient.logoutWorkshop()
    } finally {
      setWorkshopSession(null)
      setStatus('anonymous')
    }
  }, [])

  return {
    status,
    workshopSession,
    username: workshopSession?.username || null,
    error,
    setError,
    check,
    login,
    logout,
  }
}

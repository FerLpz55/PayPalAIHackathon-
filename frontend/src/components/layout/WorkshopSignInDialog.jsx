import { useEffect, useId, useRef, useState } from 'react'
import { apiClient, isSecureWorkshopTransport } from '../../services/apiClient.js'
import { clearWorkshopCredentials, setWorkshopCredentials } from '../../services/sessionStore.js'
import Button from '../ui/Button.jsx'
import Icon from '../ui/Icon.jsx'

function WorkshopSignInDialog({ onClose, onSignedIn }) {
  const titleId = useId()
  const descriptionId = useId()
  const dialogRef = useRef(null)
  const usernameRef = useRef(null)
  const onCloseRef = useRef(onClose)
  const busyRef = useRef(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const secureTransport = isSecureWorkshopTransport()

  useEffect(() => { onCloseRef.current = onClose }, [onClose])

  useEffect(() => {
    const previousFocus = document.activeElement
    const dialog = dialogRef.current
    usernameRef.current?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        if (!busyRef.current) onCloseRef.current()
        return
      }
      if (event.key !== 'Tab') return
      const items = [...dialog.querySelectorAll('button:not(:disabled), input:not(:disabled)')]
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      previousFocus?.focus?.()
    }
  }, [])

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    busyRef.current = true
    setBusy(true)
    try {
      setWorkshopCredentials(username, password)
      await apiClient.listOrdersPage({ limit: 1, offset: 0 })
      setPassword('')
      onSignedIn()
    } catch (caught) {
      clearWorkshopCredentials()
      setError(caught?.message || 'Workshop sign-in could not be verified.')
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }

  return (
    <div className="dialog-scrim" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose() }}>
      <section ref={dialogRef} className="dialog" role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId} tabIndex="-1" aria-busy={busy}>
        <button className="icon-button dialog-close" type="button" aria-label="Close dialog" onClick={onClose} disabled={busy}><Icon name="close" /></button>
        <h2 id={titleId}>Sign in to your workshop</h2>
        <p id={descriptionId}>Credentials stay in this tab's memory and are cleared when it reloads or the backend rejects them. Access is verified with a read-only order request.</p>
        <form onSubmit={submit}>
          <label className="auth-field">
            <span>Workshop username</span>
            <input ref={usernameRef} autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} disabled={busy} />
          </label>
          <label className="auth-field">
            <span>Password</span>
            <input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} />
          </label>
          {!secureTransport && <p className="field-error" role="alert">Workshop credentials require HTTPS. HTTP is allowed only for a loopback development backend.</p>}
          {error && <p className="field-error" role="alert">{error}</p>}
          <div className="dialog-actions">
            <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
            <Button variant="primary" type="submit" disabled={busy || !secureTransport}>{busy ? 'Checking access…' : 'Sign in'}</Button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default WorkshopSignInDialog

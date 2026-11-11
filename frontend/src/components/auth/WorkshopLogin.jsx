import { useState } from 'react'
import Button from '../ui/Button.jsx'
import PageHeading from '../ui/PageHeading.jsx'

function loginErrorMessage(error) {
  if (error?.status === 429) {
    return error.retryAfter
      ? `Too many sign-in attempts. Try again in ${error.retryAfter} seconds.`
      : 'Too many sign-in attempts. Wait a few minutes and try again.'
  }
  if (error?.status === 401) return 'The username or password is incorrect.'
  if (error?.status === 403) return 'This origin is not allowed to sign in. Check the backend CORS configuration.'
  if (!error?.status) return 'The backend could not be reached. Check the connection and try again.'
  return error?.message || 'The workshop could not be signed in.'
}

function WorkshopLogin({ onLogin, initialError = '' }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(initialError)

  const submit = async (event) => {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      await onLogin(username.trim(), password)
    } catch (caught) {
      setError(loginErrorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="customer-page">
      <PageHeading
        title="Workshop sign in"
        description="Sign in with the workshop credentials configured on the backend. The session is stored in an HttpOnly cookie."
      />
      <form className="panel request-form" onSubmit={submit} noValidate>
        <label className="field-label" htmlFor="workshop-username">Username</label>
        <input
          id="workshop-username"
          name="username"
          type="text"
          autoComplete="username"
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          disabled={busy}
        />
        <label className="field-label" htmlFor="workshop-password" style={{ marginTop: 14 }}>Password</label>
        <input
          id="workshop-password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={busy}
        />
        {error && <p className="inline-error" role="alert" style={{ marginTop: 14 }}>{error}</p>}
        <Button type="submit" className="full" disabled={busy || !username.trim() || !password} style={{ marginTop: 18 }}>
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>
        <p className="form-hint" style={{ marginTop: 12 }}>
          Customer links that include a token do not require a workshop session.
        </p>
      </form>
    </div>
  )
}

export default WorkshopLogin

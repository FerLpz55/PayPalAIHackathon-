import { useEffect, useRef, useState } from 'react'
import Button from '../ui/Button.jsx'
import { isConnectedMode, isDemoMode } from '../../services/apiClient.js'
import Icon from '../ui/Icon.jsx'
import DemoNotice from '../ui/DemoNotice.jsx'
import { useQuoteRequest } from '../../hooks/useQuoteRequest.js'
import { useSpeechInput } from '../../hooks/useSpeechInput.js'

function RequestForm({ onQuoteCreated }) {
  const { form, errors, status, submitError, updateField, appendDescription, submit } = useQuoteRequest()
  const speech = useSpeechInput(appendDescription)
  const isLoading = status === 'loading'
  const [attemptedSubmit, setAttemptedSubmit] = useState(false)
  const descriptionRef = useRef(null)
  const nameRef = useRef(null)
  const emailRef = useRef(null)

  useEffect(() => {
    if (!attemptedSubmit) return
    if (errors.description) descriptionRef.current?.focus()
    else if (errors.customerName) nameRef.current?.focus()
    else if (errors.customerEmail) emailRef.current?.focus()
  }, [attemptedSubmit, errors])

  async function handleSubmit(event) {
    event.preventDefault()
    setAttemptedSubmit(true)
    const quote = await submit()
    if (quote) {
      setAttemptedSubmit(false)
      onQuoteCreated(quote)
    }
  }

  return (
    <form className="panel request-form" onSubmit={handleSubmit} noValidate>
      {isDemoMode && <DemoNotice text="Demo request only. It is saved in this browser and does not call the workshop backend or generate a real AI estimate." />}
      {!isConnectedMode && !isDemoMode && (
        <p className="inline-error" role="status">Backend connection is not configured. This request cannot be submitted.</p>
      )}
      <div className="quick-suggestions-bar">
        <span className="field-label" style={{ marginBottom: 6 }}>Popular custom projects:</span>
        <div className="product-chips" style={{ marginBottom: 14 }}>
          {[
            'Solid oak dining table 1.80m x 0.90m with clear finish',
            'Floating walnut media console 2.00m with soft-close drawers',
            'Custom cedar 2-door wardrobe 1.20m x 2.00m',
          ].map((preset) => (
            <button
              key={preset}
              type="button"
              className="assistant-chip"
              disabled={isLoading}
              onClick={() => {
                updateField('description', preset)
                setAttemptedSubmit(false)
              }}
            >
              + {preset.split(' ')[0]} {preset.split(' ')[1]} {preset.split(' ')[2]}
            </button>
          ))}
        </div>
      </div>
      <label className="field-label" htmlFor="project-description">Your request <span className="required-indicator">(required)</span></label>
      <textarea
        ref={descriptionRef}
        id="project-description"
        name="description"
        required
        rows="4"
        placeholder="e.g. A two-door wardrobe in white melamine, 1.20 m wide, 1.80 m tall and 0.55 m deep, with metal handles."
        value={form.description}
        onChange={(event) => { setAttemptedSubmit(false); updateField('description', event.target.value) }}
        className={errors.description ? 'has-error' : ''}
        aria-invalid={Boolean(errors.description)}
        aria-describedby={errors.description ? 'project-description-error' : 'project-description-hint'}
        disabled={isLoading || !isConnectedMode && !isDemoMode}
      />
      <p id="project-description-hint" className="form-hint">Include the size, materials, and details you already know.</p>
      {errors.description && <p id="project-description-error" className="field-error" role="alert">{errors.description}</p>}
      <div className="request-tools">
        <span className="form-hint" aria-live="polite">{speech.message}</span>
        {speech.isSupported && (
          <button
            className={`voice-button ${speech.isListening ? 'is-listening' : ''}`}
            type="button"
            onClick={speech.isListening ? speech.stop : speech.start}
            disabled={isLoading || !isConnectedMode && !isDemoMode}
            aria-pressed={speech.isListening}
            aria-label={speech.isListening ? 'Stop voice input' : 'Speak to use voice input'}
          >
            <Icon name="mic" size={14} /> {speech.isListening ? 'Stop' : 'Speak'}
          </button>
        )}
      </div>
      <div className="customer-fields">
        <label>
          <span>Full name <span className="required-indicator">(required)</span></span>
          <input ref={nameRef} id="customer-name" name="name" autoComplete="name" required value={form.customerName} onChange={(event) => { setAttemptedSubmit(false); updateField('customerName', event.target.value) }} className={errors.customerName ? 'has-error' : ''} aria-invalid={Boolean(errors.customerName)} aria-describedby={errors.customerName ? 'customer-name-error' : undefined} disabled={isLoading || !isConnectedMode && !isDemoMode} />
          {errors.customerName && <span id="customer-name-error" className="field-error" role="alert">{errors.customerName}</span>}
        </label>
        <label>
          <span>Email for your quote <span className="required-indicator">(required)</span></span>
          <input ref={emailRef} id="customer-email" name="email" autoComplete="email" type="email" required value={form.customerEmail} onChange={(event) => { setAttemptedSubmit(false); updateField('customerEmail', event.target.value) }} className={errors.customerEmail ? 'has-error' : ''} aria-invalid={Boolean(errors.customerEmail)} aria-describedby={errors.customerEmail ? 'customer-email-error' : undefined} disabled={isLoading || !isConnectedMode && !isDemoMode} />
          {errors.customerEmail && <span id="customer-email-error" className="field-error" role="alert">{errors.customerEmail}</span>}
        </label>
      </div>
      {submitError && <p className="inline-error" role="alert">{submitError}</p>}
      <Button type="submit" disabled={isLoading || !isConnectedMode && !isDemoMode} className="full">
        {isLoading ? 'Generating AI estimate & searching live material prices…' : 'Generate instant estimate'} <Icon name="arrow" size={16} />
      </Button>
    </form>
  )
}

export default RequestForm

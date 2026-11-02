import { useEffect, useRef, useState } from 'react'
import Button from '../ui/Button.jsx'
import DemoNotice from '../ui/DemoNotice.jsx'
import Icon from '../ui/Icon.jsx'
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
        disabled={isLoading}
      />
      <p id="project-description-hint" className="form-hint">Include the size, materials, and details you already know.</p>
      {errors.description && <p id="project-description-error" className="field-error">{errors.description}</p>}
      <div className="request-tools">
        <span className="form-hint" aria-live="polite">{speech.message}</span>
        {speech.isSupported && (
          <button
            className={`voice-button ${speech.isListening ? 'is-listening' : ''}`}
            type="button"
            onClick={speech.isListening ? speech.stop : speech.start}
            disabled={isLoading}
            aria-pressed={speech.isListening}
            aria-label={speech.isListening ? 'Stop voice input' : 'Start voice input'}
          >
            <Icon name="mic" size={14} /> {speech.isListening ? 'Stop' : 'Speak'}
          </button>
        )}
      </div>
      <div className="customer-fields">
        <label>
          <span>Full name <span className="required-indicator">(required)</span></span>
          <input ref={nameRef} id="customer-name" name="name" autoComplete="name" required value={form.customerName} onChange={(event) => { setAttemptedSubmit(false); updateField('customerName', event.target.value) }} className={errors.customerName ? 'has-error' : ''} aria-invalid={Boolean(errors.customerName)} aria-describedby={errors.customerName ? 'customer-name-error' : undefined} disabled={isLoading} />
          {errors.customerName && <span id="customer-name-error" className="field-error">{errors.customerName}</span>}
        </label>
        <label>
          <span>Email for your PayPal invoice <span className="required-indicator">(required)</span></span>
          <input ref={emailRef} id="customer-email" name="email" autoComplete="email" type="email" required value={form.customerEmail} onChange={(event) => { setAttemptedSubmit(false); updateField('customerEmail', event.target.value) }} className={errors.customerEmail ? 'has-error' : ''} aria-invalid={Boolean(errors.customerEmail)} aria-describedby={errors.customerEmail ? 'customer-email-error' : undefined} disabled={isLoading} />
          {errors.customerEmail && <span id="customer-email-error" className="field-error">{errors.customerEmail}</span>}
        </label>
      </div>
      {submitError && <p className="inline-error" role="alert">{submitError}</p>}
      <Button type="submit" disabled={isLoading} className="full">
        {isLoading ? 'Preparing your demo estimate…' : 'Get my quote'} <Icon name="arrow" size={16} />
      </Button>
      <DemoNotice text="This estimate is a fixed example, not an AI-generated or workshop-approved price." />
    </form>
  )
}

export default RequestForm

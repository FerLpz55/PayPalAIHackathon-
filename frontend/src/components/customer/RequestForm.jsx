import Button from '../ui/Button.jsx'
import DemoNotice from '../ui/DemoNotice.jsx'
import Icon from '../ui/Icon.jsx'
import { useQuoteRequest } from '../../hooks/useQuoteRequest.js'
import { useSpeechInput } from '../../hooks/useSpeechInput.js'

function RequestForm({ onQuoteCreated }) {
  const { form, errors, status, submitError, updateField, appendDescription, submit } = useQuoteRequest()
  const speech = useSpeechInput(appendDescription)
  const isLoading = status === 'loading'

  async function handleSubmit(event) {
    event.preventDefault()
    const quote = await submit()
    if (quote) onQuoteCreated(quote)
  }

  return (
    <form className="panel request-form" onSubmit={handleSubmit} noValidate>
      <label className="field-label" htmlFor="project-description">Your request</label>
      <textarea
        id="project-description"
        rows="4"
        placeholder="e.g. A two-door wardrobe in white melamine, 1.20 m wide, 1.80 m tall and 0.55 m deep, with metal handles."
        value={form.description}
        onChange={(event) => updateField('description', event.target.value)}
        className={errors.description ? 'has-error' : ''}
        disabled={isLoading}
      />
      {errors.description && <p className="field-error">{errors.description}</p>}
      <div className="request-tools">
        <span className="form-hint" aria-live="polite">{speech.message}</span>
        {speech.isSupported && (
          <button
            className={`voice-button ${speech.isListening ? 'is-listening' : ''}`}
            type="button"
            onClick={speech.isListening ? speech.stop : speech.start}
            disabled={isLoading}
          >
            <Icon name="mic" size={14} /> {speech.isListening ? 'Stop' : 'Speak'}
          </button>
        )}
      </div>
      <div className="customer-fields">
        <label>
          Full name
          <input value={form.customerName} onChange={(event) => updateField('customerName', event.target.value)} className={errors.customerName ? 'has-error' : ''} disabled={isLoading} />
          {errors.customerName && <span className="field-error">{errors.customerName}</span>}
        </label>
        <label>
          Email for your PayPal invoice
          <input type="email" value={form.customerEmail} onChange={(event) => updateField('customerEmail', event.target.value)} className={errors.customerEmail ? 'has-error' : ''} disabled={isLoading} />
          {errors.customerEmail && <span className="field-error">{errors.customerEmail}</span>}
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

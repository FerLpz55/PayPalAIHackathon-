import { useQuoteRequest } from '../hooks/useQuoteRequest.js'
import { useSpeechInput } from '../hooks/useSpeechInput.js'
import './RequestForm.css'

function RequestForm({ onQuoteCreated }) {
  const { form, errors, status, submitError, updateField, appendDescription, submit } =
    useQuoteRequest()
  const speech = useSpeechInput(appendDescription)
  const isLoading = status === 'loading'

  async function handleSubmit(event) {
    event.preventDefault()
    const quote = await submit()
    if (quote && onQuoteCreated) onQuoteCreated(quote)
  }

  return (
    <form className="request-form" onSubmit={handleSubmit} noValidate>
      <span className="request-form__label">Your request</span>

      <div className={`request-form__textarea-box ${errors.description ? 'has-error' : ''}`}>
        <textarea
          id="description"
          aria-label="Describe your piece"
          placeholder="e.g. A two-door wardrobe in white melamine, 1.20 m wide, 1.80 m tall and 0.55 m deep, with metal handles."
          value={form.description}
          onChange={(event) => updateField('description', event.target.value)}
          rows={5}
          disabled={isLoading}
        />
        {speech.isSupported && (
          <button
            type="button"
            className={`request-form__voice ${speech.isListening ? 'is-listening' : ''}`}
            onClick={speech.isListening ? speech.stop : speech.start}
            disabled={isLoading}
          >
            {speech.isListening ? '■ Stop' : '● Speak'}
          </button>
        )}
      </div>
      {errors.description && <p className="request-form__error">{errors.description}</p>}
      <p className="request-form__hint">
        {speech.isSupported
          ? 'Type, or tap Speak to describe it with your voice.'
          : 'Type a description of the piece you need.'}
      </p>

      <div className="request-form__row">
        <label className="request-form__field">
          <span>Full name</span>
          <input
            type="text"
            value={form.customerName}
            onChange={(event) => updateField('customerName', event.target.value)}
            className={errors.customerName ? 'has-error' : ''}
            disabled={isLoading}
          />
          {errors.customerName && <p className="request-form__error">{errors.customerName}</p>}
        </label>
        <label className="request-form__field">
          <span>Email for your PayPal invoice</span>
          <input
            type="email"
            value={form.customerEmail}
            onChange={(event) => updateField('customerEmail', event.target.value)}
            className={errors.customerEmail ? 'has-error' : ''}
            disabled={isLoading}
          />
          {errors.customerEmail && <p className="request-form__error">{errors.customerEmail}</p>}
        </label>
      </div>

      {submitError && <p className="request-form__error request-form__error--box">{submitError}</p>}

      <button type="submit" className="request-form__submit" disabled={isLoading}>
        {isLoading ? 'Preparing your quote…' : 'Get my quote'}
      </button>
    </form>
  )
}

export default RequestForm

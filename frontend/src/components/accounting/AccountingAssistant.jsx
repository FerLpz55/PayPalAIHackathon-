import Button from '../ui/Button.jsx'
import Icon from '../ui/Icon.jsx'
import { useAccountingAssistant } from '../../hooks/useAccountingAssistant.js'
import { formatMoney } from '../../utils/format.js'

const SUGGESTIONS = [
  'How much have I collected so far?',
  'How much money is still pending?',
  'Which orders still need their deposit?',
  '¿Cuánto me falta cobrar?',
]

function AccountingAssistant() {
  const { question, setQuestion, messages, status, error, ask, maxLength } = useAccountingAssistant()
  const loading = status === 'loading'

  const handleSubmit = (event) => {
    event.preventDefault()
    ask()
  }

  return (
    <section className="panel assistant-panel" aria-labelledby="assistant-title">
      <div className="assistant-head">
        <span className="assistant-icon" aria-hidden="true">AI</span>
        <div>
          <h2 id="assistant-title">Ask TallerClaro about your money</h2>
          <p>Totals are calculated from verified PayPal payments; the AI only explains them in plain words.</p>
        </div>
      </div>

      <div className="assistant-suggestions" aria-label="Suggested questions">
        {SUGGESTIONS.map((suggestion) => (
          <button key={suggestion} type="button" className="assistant-chip" onClick={() => ask(suggestion)} disabled={loading}>
            {suggestion}
          </button>
        ))}
      </div>

      {messages.length > 0 && (
        <ol className="assistant-thread" aria-live="polite">
          {messages.map((message) => (
            <li key={message.id}>
              <p className="assistant-question">{message.question}</p>
              <div className="assistant-answer">
                {message.isDemo && <span className="assistant-demo">Demo</span>}
                <p>{message.answer}</p>
                {message.summary && (
                  <small>
                    Based on: {formatMoney(message.summary.collectedTotal)} collected · {formatMoney(message.summary.pendingToCollect)} to collect · {message.summary.ordersCount} orders
                  </small>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}

      <form className="assistant-form" onSubmit={handleSubmit} noValidate>
        <label htmlFor="assistant-question" className="sr-only">Your question</label>
        <input
          id="assistant-question"
          value={question}
          maxLength={maxLength}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="e.g. How much did I collect this month?"
          disabled={loading}
          aria-describedby={error ? 'assistant-error' : undefined}
        />
        <Button type="submit" disabled={loading}>
          {loading ? 'Thinking…' : 'Ask'} <Icon name="arrow" size={15} />
        </Button>
      </form>
      {error && <p id="assistant-error" className="inline-error" role="alert">{error}</p>}
      <p className="fine-print">Only workshop totals are shared with the AI provider, never customer names or emails. Material costs are not recorded yet, so profit is not calculated.</p>
    </section>
  )
}

export default AccountingAssistant


import { HOW_IT_WORKS_STEPS } from '../../utils/constants.js'
import { isDemoMode } from '../../services/apiClient.js'

function HowItWorks() {
  const steps = isDemoMode
    ? [
        ['Describe your custom piece', 'Enter dimensions, materials, and project details in the form.'],
        ['Review a sample estimate', 'The demo uses a fixed local example; no AI provider or live store pricing is queried.'],
        ['Simulate quote approval', 'Approval changes only local demo data and does not start a payment.'],
        ['View sample order tracking', 'Tracking is illustrative. PayPal checkout is unavailable in DEMO mode.'],
      ]
    : HOW_IT_WORKS_STEPS
  return (
    <aside className="panel how-panel">
      <h2>How it works</h2>
      <ol>
        {steps.map(([title, text], index) => (
          <li key={title}>
            <span>{index + 1}</span>
            <div><strong>{title}</strong><small>{text}</small></div>
          </li>
        ))}
      </ol>
    </aside>
  )
}

export default HowItWorks

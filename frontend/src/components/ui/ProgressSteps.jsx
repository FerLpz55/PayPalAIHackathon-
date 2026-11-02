import Icon from './Icon.jsx'
import { PROGRESS_STEPS } from '../../utils/constants.js'

function ProgressSteps({ active }) {
  return (
    <ol className="progress-steps" aria-label="Order progress">
      {PROGRESS_STEPS.map((step, index) => (
        <li className={`progress-step ${index < active ? 'complete' : ''} ${index === active ? 'current' : ''}`} key={step} aria-current={index === active ? 'step' : undefined}>
          <span className="progress-node" aria-hidden="true">{index < active ? <Icon name="check" size={12} /> : null}</span>
          <small>{step}</small>
        </li>
      ))}
    </ol>
  )
}

export default ProgressSteps

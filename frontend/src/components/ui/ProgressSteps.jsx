import Icon from './Icon.jsx'
import { PROGRESS_STEPS } from '../../utils/constants.js'

function ProgressSteps({ active }) {
  return (
    <div className="progress-steps">
      {PROGRESS_STEPS.map((step, index) => (
        <div className={`progress-step ${index <= active ? 'complete' : ''}`} key={step}>
          <span className="progress-node">{index < active ? <Icon name="check" size={12} /> : null}</span>
          <small>{step}</small>
        </div>
      ))}
    </div>
  )
}

export default ProgressSteps

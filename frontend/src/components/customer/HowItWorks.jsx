import { HOW_IT_WORKS_STEPS } from '../../utils/constants.js'

function HowItWorks() {
  return (
    <aside className="panel how-panel">
      <h2>How it works</h2>
      <ol>
        {HOW_IT_WORKS_STEPS.map(([title, text], index) => (
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

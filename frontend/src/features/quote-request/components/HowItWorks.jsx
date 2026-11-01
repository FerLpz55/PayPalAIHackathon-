import './HowItWorks.css'

const STEPS = [
  { title: 'Describe your piece', text: 'By text or voice.' },
  { title: 'Receive a clear quote', text: 'Materials, labor and total, approved by the workshop.' },
  { title: 'Pay a 50% deposit with PayPal', text: 'Work starts as soon as it is paid.' },
  { title: 'Follow every expense', text: 'See the material receipts paid with your deposit.' },
  { title: 'Pay the balance when finished', text: 'Your deposit is already discounted.' },
]

function HowItWorks() {
  return (
    <aside className="how-it-works">
      <h2>How it works</h2>
      <ol>
        {STEPS.map((step, index) => (
          <li key={step.title}>
            <span className="how-it-works__number">{index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <p>{step.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </aside>
  )
}

export default HowItWorks

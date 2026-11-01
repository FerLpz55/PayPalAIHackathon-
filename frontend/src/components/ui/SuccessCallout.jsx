import Icon from './Icon.jsx'

function SuccessCallout({ title, text }) {
  return (
    <div className="success-callout">
      <span className="check-dot"><Icon name="check" size={13} /></span>
      <div>
        <strong>{title}</strong>
        <small>{text}</small>
      </div>
    </div>
  )
}

export default SuccessCallout

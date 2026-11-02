import Icon from './Icon.jsx'

function EmptyState({ title, text, action }) {
  return (
    <div className="empty-state">
      <span className="empty-icon"><Icon name="file" size={22} /></span>
      <h2>{title}</h2>
      <p>{text}</p>
      {action}
    </div>
  )
}

export default EmptyState

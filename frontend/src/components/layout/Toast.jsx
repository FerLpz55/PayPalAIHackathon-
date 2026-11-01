import Icon from '../ui/Icon.jsx'

function Toast({ error, notice, onDismiss }) {
  if (!error && !notice) return null
  return (
    <div className={`toast ${error ? 'toast-error' : 'toast-success'}`} role={error ? 'alert' : 'status'}>
      <span>{error || notice}</span>
      <button aria-label="Dismiss message" onClick={onDismiss}><Icon name="close" size={15} /></button>
    </div>
  )
}

export default Toast

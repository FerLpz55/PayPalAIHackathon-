import Button from './Button.jsx'
import Icon from './Icon.jsx'

function ConfirmDialog({ title, text, confirmLabel, onConfirm, onClose }) {
  return (
    <div className="dialog-scrim" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <button className="icon-button dialog-close" aria-label="Close dialog" onClick={onClose}><Icon name="close" /></button>
        <h2 id="dialog-title">{title}</h2>
        <p>{text}</p>
        <div className="dialog-actions">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="success" onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </section>
    </div>
  )
}

export default ConfirmDialog

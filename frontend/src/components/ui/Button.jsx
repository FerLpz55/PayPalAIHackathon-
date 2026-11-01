import Icon from './Icon.jsx'

function Button({ children, onClick, variant = 'primary', disabled = false, type = 'button', icon, className = '' }) {
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`button button-${variant} ${className}`}>
      {icon && <Icon name={icon} size={16} />}
      {children}
    </button>
  )
}

export default Button

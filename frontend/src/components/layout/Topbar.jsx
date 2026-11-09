import Icon from '../ui/Icon.jsx'
import { TOPBAR_LABELS } from '../../utils/constants.js'
import { isDemoMode } from '../../services/apiClient.js'

function Topbar({ route, onMenu, menuOpen, menuButtonRef, username, onLogout }) {
  const [section, defaultHeading] = TOPBAR_LABELS[route.split('/')[0]] || TOPBAR_LABELS.dashboard
  const heading = !isDemoMode && route.split('/')[0] === 'dashboard' ? 'Dashboard' : defaultHeading
  const displayName = isDemoMode ? 'Alex' : (username || 'Workshop')
  return (
    <header className="topbar">
      <button ref={menuButtonRef} className="icon-button menu-button" type="button" onClick={onMenu} aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-controls="workshop-navigation" aria-expanded={menuOpen}>
        <Icon name={menuOpen ? 'close' : 'menu'} />
      </button>
      <div>
        <div className="breadcrumb">{section} <span aria-hidden="true">/</span> TallerClaro</div>
        <div className="topbar-title">{heading}</div>
      </div>
      <div className="user-menu">
        <span>{displayName}</span>
        <span className="user-avatar" aria-hidden="true">{displayName.charAt(0).toUpperCase()}</span>
        {onLogout && (
          <button type="button" className="table-action" onClick={() => void onLogout()} aria-label="Sign out of the workshop session">
            Sign out
          </button>
        )}
      </div>
    </header>
  )
}

export default Topbar

import Icon from '../ui/Icon.jsx'
import { TOPBAR_LABELS } from '../../utils/constants.js'
import { isDemoMode } from '../../services/apiClient.js'

function Topbar({ route, onMenu, menuOpen, menuButtonRef, workshopAuthenticated, onSignIn, onSignOut }) {
  const [section, defaultHeading] = TOPBAR_LABELS[route.split('/')[0]] || TOPBAR_LABELS.dashboard
  const heading = !isDemoMode && route.split('/')[0] === 'dashboard' ? 'Dashboard' : defaultHeading
  return (
    <header className="topbar">
      <button ref={menuButtonRef} className="icon-button menu-button" type="button" onClick={onMenu} aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-controls="workshop-navigation" aria-expanded={menuOpen}>
        <Icon name={menuOpen ? 'close' : 'menu'} />
      </button>
      <div>
        <div className="breadcrumb">{section} <span aria-hidden="true">/</span> TallerClaro</div>
        <div className="topbar-title">{heading}</div>
      </div>
      {isDemoMode
        ? <div className="user-menu"><span>Alex</span><span className="user-avatar" aria-hidden="true">A</span></div>
        : <button className="user-menu user-menu-auth" type="button" onClick={workshopAuthenticated ? onSignOut : onSignIn} aria-label={workshopAuthenticated ? 'Sign out of workshop' : 'Sign in to workshop'}>
            <span>{workshopAuthenticated ? 'Sign out' : 'Sign in'}</span><span className="user-avatar" aria-hidden="true">W</span>
          </button>}
    </header>
  )
}

export default Topbar

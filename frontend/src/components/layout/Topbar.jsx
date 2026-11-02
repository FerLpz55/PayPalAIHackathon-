import Icon from '../ui/Icon.jsx'
import { TOPBAR_LABELS } from '../../utils/constants.js'

function Topbar({ route, onMenu, menuOpen, menuButtonRef }) {
  const [section, heading] = TOPBAR_LABELS[route.split('/')[0]] || TOPBAR_LABELS.dashboard
  return (
    <header className="topbar">
      <button ref={menuButtonRef} className="icon-button menu-button" type="button" onClick={onMenu} aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-controls="workshop-navigation" aria-expanded={menuOpen}>
        <Icon name={menuOpen ? 'close' : 'menu'} />
      </button>
      <div>
        <div className="breadcrumb">{section} <span>/</span> TallerClaro</div>
        <div className="topbar-title">{heading}</div>
      </div>
      <div className="user-menu"><span>Alex</span><span className="user-avatar">A</span></div>
    </header>
  )
}

export default Topbar

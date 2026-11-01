import Icon from '../ui/Icon.jsx'
import { NAV_ITEMS } from '../../utils/constants.js'

function Sidebar({ active, open, onClose, go }) {
  return (
    <>
      <div className={`nav-scrim ${open ? 'show' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <span className="brand-mark">T</span>
          <span>TallerClaro</span>
          <button className="icon-button mobile-close" onClick={onClose} aria-label="Close navigation"><Icon name="close" /></button>
        </div>
        <div className="nav-caption">Workspace</div>
        <nav aria-label="Workshop navigation">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.id}
              href={`#/${item.id}`}
              onClick={(event) => { event.preventDefault(); go(item.id) }}
              className={`nav-link ${active === item.id ? 'active' : ''}`}
              aria-current={active === item.id ? 'page' : undefined}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </a>
          ))}
        </nav>
        <div className="workshop-block">
          <div className="nav-caption">Your workshop</div>
          <div className="workshop">
            <span className="workshop-avatar">M</span>
            <span><strong>Madera Norte</strong><small>Carpentry studio</small></span>
          </div>
        </div>
        <div className="sidebar-bottom">
          <h3>Need a hand?</h3>
          <p>Your AI assistant is here to help.</p>
          <button className="button button-subtle full" onClick={() => go('customer/new')}>Ask TallerClaro</button>
          <div className="demo-pill"><span /> Demo workspace</div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar

import { useEffect, useRef } from 'react'
import Icon from '../ui/Icon.jsx'
import { NAV_ITEMS } from '../../utils/constants.js'

function Sidebar({ active, open, onClose, go, triggerRef }) {
  const sidebarRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const sidebar = sidebarRef.current
    const trigger = triggerRef.current
    const focusable = () => [...sidebar.querySelectorAll('a[href], button:not(:disabled)')]
    sidebar.querySelector('.mobile-close')?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key !== 'Tab') return
      const items = focusable()
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      trigger?.focus()
    }
  }, [open, onClose, triggerRef])

  return (
    <>
      <button className={`nav-scrim ${open ? 'show' : ''}`} type="button" aria-label="Close navigation" aria-hidden={!open} tabIndex={open ? 0 : -1} disabled={!open} onClick={onClose} />
      <aside ref={sidebarRef} className={`sidebar ${open ? 'sidebar-open' : ''}`} aria-label="Workshop sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">T</span>
          <span>TallerClaro</span>
          <button className="icon-button mobile-close" type="button" onClick={onClose} aria-label="Close navigation"><Icon name="close" /></button>
        </div>
        <div className="nav-caption">Workspace</div>
        <nav id="workshop-navigation" aria-label="Workshop navigation">
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
          <p>Ask the AI assistant about your money.</p>
          <button className="button button-subtle full" onClick={() => go('accounting')}>Ask TallerClaro</button>
          <div className="demo-pill"><span /> Demo workspace</div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar

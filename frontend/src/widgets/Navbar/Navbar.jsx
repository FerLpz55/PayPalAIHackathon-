import './Navbar.css'

function Navbar({ workshopName, workshopType }) {
  return (
    <header className="navbar">
      <div className="navbar__brand">
        <span className="navbar__logo">T</span>
        <span className="navbar__name">TallerClaro</span>
      </div>
      {workshopName && (
        <div className="navbar__workshop">
          <span className="navbar__avatar">{workshopName.charAt(0)}</span>
          <span>
            Ordering from <strong>{workshopName}</strong>
            {workshopType && ` · ${workshopType}`}
          </span>
        </div>
      )}
    </header>
  )
}

export default Navbar

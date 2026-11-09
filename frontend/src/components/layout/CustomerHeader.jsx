function CustomerHeader({ workshopName = 'Madera Norte', workshopType = 'Carpentry studio' }) {
  return (
    <header className="customer-header">
      <a className="brand" href="#/dashboard"><span className="brand-mark" aria-hidden="true">T</span><span>TallerClaro</span></a>
      <a className="customer-workshop" href="#/dashboard">
        <span className="workshop-avatar" aria-hidden="true">{workshopName.charAt(0)}</span>{` Ordering from ${workshopName} · ${workshopType}`}
      </a>
    </header>
  )
}

export default CustomerHeader

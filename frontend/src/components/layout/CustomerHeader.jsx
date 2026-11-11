import { WORKSHOP_PROFILE } from '../../utils/constants.js'

function CustomerHeader({ workshopName = WORKSHOP_PROFILE.name, workshopType = WORKSHOP_PROFILE.type }) {
  return (
    <header className="customer-header">
      <a className="brand" href="#/customer/new"><span className="brand-mark" aria-hidden="true">T</span><span>TallerClaro</span></a>
      <a className="customer-workshop" href="#/customer/new">
        <span className="workshop-avatar" aria-hidden="true">{workshopName.charAt(0)}</span>{` Ordering from ${workshopName} · ${workshopType}`}
      </a>
    </header>
  )
}

export default CustomerHeader

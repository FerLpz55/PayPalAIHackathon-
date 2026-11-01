import { STATUS_LABELS } from '../../utils/constants.js'

function Status({ value }) {
  return <span className={`status status-${value}`}>{STATUS_LABELS[value] || value}</span>
}

export default Status

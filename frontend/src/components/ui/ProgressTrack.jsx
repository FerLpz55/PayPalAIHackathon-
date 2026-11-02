function ProgressTrack({ value, total, label = 'Progress' }) {
  const max = Math.max(total || 0, 1)
  const current = Math.min(max, Math.max(0, value || 0))
  const percent = Math.min(100, (current / max) * 100)
  return (
    <div className="progress-track" role="progressbar" aria-label={label} aria-valuemin="0" aria-valuemax={max} aria-valuenow={current} aria-valuetext={`${Math.round(percent)}%`}>
      <span style={{ width: `${percent}%` }} />
    </div>
  )
}

export default ProgressTrack

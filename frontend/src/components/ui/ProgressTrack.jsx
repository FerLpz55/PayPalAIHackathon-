function ProgressTrack({ value, total }) {
  const percent = total ? Math.min(100, (value / total) * 100) : 0
  return (
    <div className="progress-track">
      <span style={{ width: `${percent}%` }} />
    </div>
  )
}

export default ProgressTrack

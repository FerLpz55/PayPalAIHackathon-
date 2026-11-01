function Metric({ label, value, detail, tone = '' }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
      <small>{detail}</small>
    </div>
  )
}

export default Metric

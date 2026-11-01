function DataLine({ label, value }) {
  return (
    <div className="data-line">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export default DataLine

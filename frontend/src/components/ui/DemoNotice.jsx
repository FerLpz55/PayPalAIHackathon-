function DemoNotice({ text }) {
  if (!text) return null
  return (
    <aside className="demo-notice" role="note" aria-label="Demo mode notice">
      <span className="demo-notice-label">DEMO</span>
      <span>{text}</span>
    </aside>
  )
}

export default DemoNotice

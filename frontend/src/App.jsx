import { useCallback, useEffect, useState } from 'react'
import { mockApi } from './services/mockApi'
import './App.css'

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: 'grid' },
  { id: 'orders', label: 'Orders', icon: 'clipboard' },
  { id: 'quotes', label: 'Quotes', icon: 'file' },
  { id: 'receipts', label: 'Receipts', icon: 'receipt' },
  { id: 'accounting', label: 'Accounting', icon: 'chart' },
]
const statusLabels = { pending: 'Pending', quote_sent: 'Quote sent', paid: 'Paid', in_progress: 'In production', ready_to_finish: 'Ready to finish', delivered: 'Delivered' }
const formatMoney = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value || 0)

function Icon({ name, size = 18 }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    clipboard: <><rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1M8 10h8M8 14h8M8 18h5"/></>,
    file: <><path d="M13 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10z"/><path d="M13 3v7h7M8 14h8M8 18h8"/></>,
    receipt: <><path d="M5 3h14v18l-3-2-4 2-4-2-3 2z"/><path d="M8 8h8M8 12h8M8 16h5"/></>,
    chart: <><path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/></>,
    plus: <path d="M12 5v14M5 12h14"/>, search: <><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>, check: <path d="m5 12 4 4L19 6"/>,
    upload: <><path d="M12 16V4m-5 5 5-5 5 5"/><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/></>,
    mic: <><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11v1a7 7 0 0 0 14 0v-1M12 19v3m-4 0h8"/></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16"/></>,
    close: <><path d="m6 6 12 12M18 6 6 18"/></>,
  }
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name] || paths.file}</svg>
}

function App() {
  const [route, setRoute] = useState(() => window.location.hash.replace('#/', '') || 'dashboard')
  const [orders, setOrders] = useState([])
  const [quote, setQuote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [orderData, quoteData] = await Promise.all([mockApi.listOrders(), mockApi.getQuote()])
      setOrders(orderData)
      setQuote(quoteData)
      setError('')
    } catch { setError('Your demo data could not be loaded. Refresh the page to try again.') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { const timer = window.setTimeout(() => { void refresh() }, 0); return () => window.clearTimeout(timer) }, [refresh])
  useEffect(() => {
    const readRoute = () => { setRoute(window.location.hash.replace('#/', '') || 'dashboard'); setMobileNavOpen(false) }
    window.addEventListener('hashchange', readRoute)
    return () => window.removeEventListener('hashchange', readRoute)
  }, [])
  useEffect(() => {
    if (!notice) return undefined
    const timer = window.setTimeout(() => setNotice(''), 3600)
    return () => window.clearTimeout(timer)
  }, [notice])

  const go = (next) => { window.location.hash = `/${next}`; setRoute(next) }
  const mutate = async (action, success) => {
    setError('')
    try { await action(); await refresh(); setNotice(success) }
    catch (caught) { setError(caught.message || 'Something went wrong. Please try again.') }
  }
  const actions = { go, mutate, setNotice, setError, refresh }
  const customer = route.startsWith('customer/')
  const content = (() => {
    if (customer) return <CustomerFlow route={route} quote={quote} orders={orders} loading={loading} actions={actions} />
    if (route === 'dashboard') return <Dashboard orders={orders} loading={loading} actions={actions} />
    if (route === 'orders') return <OrdersPage orders={orders} loading={loading} actions={actions} />
    if (route === 'quotes') return <QuotesPage orders={orders} quote={quote} loading={loading} actions={actions} />
    if (route === 'receipts') return <ReceiptsPage orders={orders} loading={loading} actions={actions} />
    if (route === 'accounting') return <AccountingPage orders={orders} loading={loading} actions={actions} />
    if (route.startsWith('order/')) return <OrderDetail id={route.split('/')[1]} orders={orders} loading={loading} actions={actions} />
    return <Dashboard orders={orders} loading={loading} actions={actions} />
  })()

  return <div className={customer ? 'app customer-app' : 'app'}>
    {!customer && <Sidebar active={route.split('/')[0]} open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} go={go} />}
    <main className="main-area">
      {customer ? <CustomerHeader /> : <Topbar title={route} onMenu={() => setMobileNavOpen(!mobileNavOpen)} />}
      {(error || notice) && <div className={`toast ${error ? 'toast-error' : 'toast-success'}`} role={error ? 'alert' : 'status'}><span>{error || notice}</span><button aria-label="Dismiss message" onClick={() => { setError(''); setNotice('') }}><Icon name="close" size={15} /></button></div>}
      {content}
    </main>
  </div>
}

function Sidebar({ active, open, onClose, go }) {
  return <><div className={`nav-scrim ${open ? 'show' : ''}`} onClick={onClose} />
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="brand"><span className="brand-mark">T</span><span>TallerClaro</span><button className="icon-button mobile-close" onClick={onClose} aria-label="Close navigation"><Icon name="close" /></button></div>
      <div className="nav-caption">Workspace</div>
      <nav aria-label="Workshop navigation">{navItems.map((item) => <a key={item.id} href={`#/${item.id}`} onClick={(event) => { event.preventDefault(); go(item.id) }} className={`nav-link ${active === item.id ? 'active' : ''}`} aria-current={active === item.id ? 'page' : undefined}><Icon name={item.icon} /><span>{item.label}</span></a>)}</nav>
      <div className="workshop-block"><div className="nav-caption">Your workshop</div><div className="workshop"><span className="workshop-avatar">M</span><span><strong>Madera Norte</strong><small>Carpentry studio</small></span></div></div>
      <div className="sidebar-bottom"><h3>Need a hand?</h3><p>Your AI assistant is here to help.</p><button className="button button-subtle full" onClick={() => go('customer/new')}>Ask TallerClaro</button><div className="demo-pill"><span /> Demo workspace</div></div>
    </aside></>
}

function Topbar({ title, onMenu }) {
  const labels = { dashboard: ['Dashboard', 'Good morning, Alex'], orders: ['Orders', 'Your workshop orders'], quotes: ['Quotes', 'Review and prepare quotes'], receipts: ['Receipts', 'Materials and order receipts'], accounting: ['Accounting', 'Your workshop finances'], order: ['Orders', 'Order details'] }
  const [section, heading] = labels[title.split('/')[0]] || labels.dashboard
  return <header className="topbar"><button className="icon-button menu-button" onClick={onMenu} aria-label="Open navigation"><Icon name="menu" /></button><div><div className="breadcrumb">{section} <span>/</span> TallerClaro</div><div className="topbar-title">{heading}</div></div><div className="user-menu"><span>Alex</span><span className="user-avatar">A</span></div></header>
}

function CustomerHeader() { return <header className="customer-header"><a className="brand" href="#/dashboard"><span className="brand-mark">T</span><span>TallerClaro</span></a><a className="customer-workshop" href="#/dashboard"><span className="workshop-avatar">M</span> Ordering from Madera Norte · Carpentry studio</a></header> }
function PageHeading({ title, description, action }) { return <div className="page-heading"><div><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div> }
function Button({ children, onClick, variant = 'primary', disabled = false, type = 'button', icon, className = '' }) { return <button type={type} onClick={onClick} disabled={disabled} className={`button button-${variant} ${className}`}>{icon && <Icon name={icon} size={16} />}{children}</button> }
function Status({ value }) { return <span className={`status status-${value}`}>{statusLabels[value] || value}</span> }
function LoadingState() { return <div className="loading-line" role="status">Loading your demo workspace…</div> }
function EmptyState({ title, text, action }) { return <div className="empty-state"><span className="empty-icon"><Icon name="file" size={22} /></span><h3>{title}</h3><p>{text}</p>{action}</div> }

function Dashboard({ orders, loading, actions }) {
  const active = orders.filter((order) => ['pending', 'quote_sent', 'paid', 'in_progress', 'ready_to_finish'].includes(order.status)).length
  const review = orders.filter((order) => order.status === 'quote_sent').length
  const received = orders.reduce((sum, order) => sum + order.paid, 0)
  const attention = orders.filter((order) => order.status === 'ready_to_finish').length
  return <div className="page-content"><PageHeading title="Good morning, Alex" description="A clear view of every job, from first request to final payment." />
    <section className="composer panel"><div className="composer-copy"><h2>What would you like to make?</h2><p>Start an order and prepare a quote for your customer.</p></div><button className="composer-action" onClick={() => actions.go('customer/new')} aria-label="Create a new order"><Icon name="plus" /><span>New order</span></button><button className="composer-text" onClick={() => actions.go('customer/new')}>Describe the project to get started…</button><div className="composer-footer"><span>Type a request to create a demo quote</span><Button onClick={() => actions.go('customer/new')}>Create with AI <Icon name="arrow" size={15} /></Button></div></section>
    <section className="metric-row" aria-label="Workshop summary"><Metric label="Active orders" value={String(active).padStart(2, '0')} detail="Across all stages"/><Metric label="Quotes to review" value={String(review).padStart(2, '0')} detail="Waiting for an advance" tone="blue"/><Metric label="Payments received" value={formatMoney(received)} detail="Illustrative demo figures" tone="green"/><Metric label="Needs attention" value={String(attention).padStart(2, '0')} detail="Ready to finish" /></section>
    <div className="section-head"><div><h2>Your orders</h2><p>A quick look at the work moving through your shop.</p></div><a className="text-link" href="#/orders" onClick={(e) => { e.preventDefault(); actions.go('orders') }}>View all orders <Icon name="arrow" size={14}/></a></div>
    <div className="panel table-panel">{loading ? <LoadingState /> : <><OrdersTable orders={orders.slice(0, 4)} actions={actions} /><div className="table-footer">Showing {Math.min(4, active)} of {active} active orders</div></>}</div>
    <DemoNotice text="Sample orders and totals are stored in this browser for demonstration. They are not connected to a workshop backend." />
  </div>
}
function Metric({ label, value, detail, tone = '' }) { return <div className="metric"><span>{label}</span><strong className={tone}>{value}</strong><small>{detail}</small></div> }
function OrdersTable({ orders, actions }) {
  if (!orders.length) return <EmptyState title="No orders yet" text="Create a quote to see its order here." action={<Button onClick={() => actions.go('customer/new')}>Start an order</Button>} />
  return <div className="table-scroll"><table><thead><tr><th>Order</th><th>Client</th><th>Total</th><th>Status</th><th>Next step</th></tr></thead><tbody>{orders.map((order) => <tr key={order.id}><td><a href={`#/order/${order.id}`} className="order-id" onClick={(e) => { e.preventDefault(); actions.go(`order/${order.id}`) }}>{order.id}</a><span className="project-cell">{order.project}</span></td><td>{order.customer}</td><td className="amount-cell">{formatMoney(order.amount)}</td><td><Status value={order.status}/></td><td><button className="table-action" onClick={() => actions.go(`order/${order.id}`)}>{order.next}</button></td></tr>)}</tbody></table></div>
}
function DemoNotice({ text }) { return <p className="demo-notice"><span className="demo-dot"/> Demo only · {text}</p> }

function OrdersPage({ orders, loading, actions }) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const filtered = orders.filter((order) => `${order.id} ${order.customer} ${order.project}`.toLowerCase().includes(query.toLowerCase()) && (filter === 'all' || order.status === filter))
  return <div className="page-content"><PageHeading title="Your orders" description="Keep every project moving and see what needs attention." action={<Button icon="plus" onClick={() => actions.go('customer/new')}>New order</Button>} />
    <div className="toolbar"><label className="search-field"><Icon name="search"/><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search orders or customers" aria-label="Search orders or customers" /></label><label className="select-label"><span className="sr-only">Filter by status</span><select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="all">All statuses</option>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><span className="results-count">{filtered.length} orders</span></div>
    <div className="panel table-panel">{loading ? <LoadingState/> : <OrdersTable orders={filtered} actions={actions}/>}</div><DemoNotice text="Status updates are saved in local demo data and do not contact a backend."/>
  </div>
}

function QuotesPage({ orders, quote, loading, actions }) {
  const quoteOrders = orders.filter((order) => order.status === 'quote_sent' || order.status === 'pending')
  return <div className="page-content"><PageHeading title="Quotes" description="Review estimates and keep customers informed." action={<Button icon="plus" onClick={() => actions.go('customer/new')}>Create quote</Button>} />
    {loading ? <LoadingState/> : <>
      {quote && <section className="panel quote-list-feature"><div><span className="eyebrow">Latest demo quote · {quote.id}</span><h2>{quote.project}</h2><p>{quote.customer} · Created just now · Estimate for workshop review</p></div><strong>{formatMoney(quote.total)}</strong><Button onClick={() => actions.go('customer/quote')}>Review quote <Icon name="arrow" size={15}/></Button></section>}
      <div className="section-head"><div><h2>Waiting for approval</h2><p>These customers have a quote ready for their next step.</p></div></div>
      <div className="panel table-panel">{quoteOrders.length ? <OrdersTable orders={quoteOrders} actions={actions}/> : <EmptyState title="No quotes waiting" text="New estimates will appear here after you create them." action={<Button onClick={() => actions.go('customer/new')}>Create a quote</Button>}/>}</div>
    </>}<DemoNotice text="The demo estimate is illustrative. The backend must validate all pricing before a quote can be paid."/>
  </div>
}

function ReceiptsPage({ orders, loading, actions }) {
  const [selected, setSelected] = useState('TC-1048')
  const order = orders.find((item) => item.id === selected) || orders[0]
  const addFiles = async (event) => {
    const files = [...event.target.files || []]
    if (!files.length || !order) return
    for (const file of files) await actions.mutate(() => mockApi.addReceipt(order.id, file), `${file.name} added to the demo receipt list.`)
    event.target.value = ''
  }
  return <div className="page-content"><PageHeading title="Material receipts" description="Keep purchase records alongside the orders they support." />
    <div className="toolbar"><label className="select-label"><span className="sr-only">Choose an order</span><select value={order?.id || ''} onChange={(e) => setSelected(e.target.value)}>{orders.map((item) => <option key={item.id} value={item.id}>{item.id} · {item.project}</option>)}</select></label><span className="results-count">Files stay in this browser demo</span></div>
    {loading ? <LoadingState/> : order && <div className="receipt-layout"><section className="panel receipt-main"><div className="section-head"><div><h2>{order.project}</h2><p>{order.id} · {order.customer}</p></div><Status value={order.status}/></div><label className="upload-area"><input type="file" accept="image/png,image/jpeg,application/pdf" multiple onChange={addFiles}/><span className="upload-icon"><Icon name="upload" size={20}/></span><strong>Drop receipt photos here, or browse files</strong><small>JPG, PNG or PDF · Files are listed locally in this demo</small><span className="button button-secondary">Choose receipts</span></label><h3 className="list-label">Uploaded receipts <span>{order.receipts.length}</span></h3>{order.receipts.length ? <div className="receipt-list">{order.receipts.map((receipt) => <div className="receipt-row" key={receipt.id}><span className={`receipt-check ${receipt.state}`}><Icon name={receipt.state === 'verified' ? 'check' : 'receipt'} size={15}/></span><div><strong>{receipt.label}</strong><small>{receipt.id} · {receipt.date} · {receipt.state === 'verified' ? 'Sample status' : 'Awaiting backend review'}</small></div><b>{receipt.amount ? formatMoney(receipt.amount) : '—'}</b><Status value={receipt.state === 'verified' ? 'paid' : 'pending'}/></div>)}</div> : <EmptyState title="No receipts attached" text="Upload a photo or PDF to add it to this local demo order."/>}</section>
      <aside className="panel spending-panel"><h2>Spending overview</h2><p>Compare receipt entries with the advance.</p><div className="success-callout"><span className="check-dot"><Icon name="check" size={13}/></span><div><strong>Demo receipt summary</strong><small>Amounts are not verified by an AI service.</small></div></div><DataLine label="Advance received" value={formatMoney(order.paid)}/><DataLine label="Receipt amounts" value={formatMoney(order.spent)}/><div className="progress-track"><span style={{ width: `${Math.min(100, order.paid ? Math.round(order.spent / order.paid * 100) : 0)}%` }} /></div><p className="fine-print">A connected backend must securely store uploaded files and verify each amount against the approved quote.</p></aside></div>}
  </div>
}
function DataLine({ label, value }) { return <div className="data-line"><span>{label}</span><strong>{value}</strong></div> }

function AccountingPage({ orders, loading, actions }) {
  const [showFinish, setShowFinish] = useState(false)
  const ready = orders.find((order) => order.status === 'ready_to_finish')
  const received = orders.reduce((sum, order) => sum + order.paid, 0)
  const spent = orders.reduce((sum, order) => sum + order.spent, 0)
  const earned = received - spent
  const monthly = [
    { month: 'Jul', in: 7100, out: 3400 }, { month: 'Aug', in: 8200, out: 4100 },
    { month: 'Sep', in: 7600, out: 3800 }, { month: 'Oct', in: Math.max(received, 1000), out: Math.max(spent, 600) },
  ]
  const highest = Math.max(...monthly.map((item) => item.in))
  const finish = async () => { if (!ready) return; await actions.mutate(() => mockApi.updateStatus(ready.id, 'delivered'), 'Order marked delivered in demo data. No payment was charged.'); setShowFinish(false) }
  return <div className="page-content"><PageHeading title="Finish the work. See what you earned." description="Track demo payments and workshop expenses in one place." />
    {ready && <section className="panel finish-banner"><div><span className="success-kicker"><Icon name="check" size={14}/> Ready to finish</span><h2>{ready.project}</h2><p>{ready.id} · {ready.customer} · Advance paid {formatMoney(ready.paid)}</p><small>Mark the work complete to update its demo status. Final payment is not processed here.</small></div><Button variant="success" onClick={() => setShowFinish(true)}>Mark as finished</Button></section>}
    <div className="section-head accounting-heading"><div><h2>Your month, made simple</h2><p>October 2026 · Illustrative demo figures</p></div></div>
    {loading ? <LoadingState/> : <>
      <section className="metric-row accounting-metrics"><Metric label="Money received" value={formatMoney(received)} detail="Customer payments" tone="green"/><Metric label="Money spent" value={formatMoney(spent)} detail="Uploaded receipt amounts"/><Metric label="Remaining" value={formatMoney(earned)} detail="Received minus entered expenses" tone="green"/></section>
      <div className="accounting-grid"><section className="panel chart-panel"><h3>Income and spending</h3><p>Sample monthly amounts for this demonstration.</p><div className="chart" role="img" aria-label="Illustrative income and spending comparison from July to October">{monthly.map((month) => <div className="chart-month" key={month.month}><div className="bars"><span className="bar income" style={{ height: `${Math.max(8, month.in / highest * 100)}%` }} title={`Received ${formatMoney(month.in)}`}/><span className="bar expense" style={{ height: `${Math.max(8, month.out / highest * 100)}%` }} title={`Spent ${formatMoney(month.out)}`}/></div><small>{month.month}</small></div>)}</div><div className="chart-legend"><span><i className="legend-income"/> Received</span><span><i className="legend-expense"/> Spent</span></div></section>
        <section className="panel expense-panel"><h3>Where it went</h3><p>Receipt amounts currently entered in the demo.</p>{[['Materials', Math.min(spent, 4200)], ['Workshop costs', Math.max(0, spent - 4200)], ['Other expenses', 0]].map(([label, amount]) => <div className="expense-item" key={label}><DataLine label={label} value={formatMoney(amount)}/><div className="progress-track"><span style={{ width: `${spent ? Math.min(100, amount / spent * 100) : 0}%` }}/></div></div>)}<div className="info-callout">Your money stays in your PayPal account. No live payment information is shown in this demo.</div></section></div>
    </>}
    {showFinish && <div className="dialog-scrim" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setShowFinish(false) }}><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="finish-title"><button className="icon-button dialog-close" aria-label="Close dialog" onClick={() => setShowFinish(false)}><Icon name="close"/></button><h2 id="finish-title">Mark this order as finished?</h2><p>This updates the sample order status in your browser. It will not send an invoice or charge the customer.</p><div className="dialog-actions"><Button variant="secondary" onClick={() => setShowFinish(false)}>Cancel</Button><Button variant="success" onClick={finish}>Mark as finished</Button></div></section></div>}
  </div>
}

function OrderDetail({ id, orders, loading, actions }) {
  const order = orders.find((item) => item.id === id)
  const choices = ['pending', 'quote_sent', 'paid', 'in_progress', 'ready_to_finish', 'delivered']
  if (loading) return <div className="page-content"><LoadingState/></div>
  if (!order) return <div className="page-content"><EmptyState title="Order not found" text="This order may have been removed from the local demo data." action={<Button onClick={() => actions.go('orders')}>Back to orders</Button>}/></div>
  const step = Math.max(0, ['quote_sent', 'paid', 'in_progress', 'ready_to_finish', 'delivered'].indexOf(order.status))
  return <div className="page-content"><PageHeading title={order.id} description={`${order.customer} · ${order.project}`} action={<Status value={order.status}/>}/><section className="panel progress-panel"><h2>Order progress</h2><ProgressSteps active={step}/></section>
    <div className="detail-grid"><section className="panel detail-panel"><div className="section-head"><div><h2>Project details</h2><p>Estimate and payment summary</p></div></div><DataLine label="Project" value={order.project}/><DataLine label="Customer" value={order.customer}/><DataLine label="Estimated total" value={formatMoney(order.amount)}/><DataLine label="Advance received" value={formatMoney(order.paid)}/><DataLine label="Balance due" value={formatMoney(Math.max(order.amount - order.paid, 0))}/><label className="status-editor">Update demo status<select value={order.status} onChange={(e) => actions.mutate(() => mockApi.updateStatus(order.id, e.target.value), `Order ${order.id} status updated in demo data.`)}>{choices.map((choice) => <option key={choice} value={choice}>{statusLabels[choice]}</option>)}</select></label></section>
      <section className="panel detail-panel"><h2>Material receipts</h2><p>Receipt uploads are local demo records.</p>{order.receipts.length ? order.receipts.map((item) => <div className="mini-receipt" key={item.id}><span>{item.label}</span><strong>{formatMoney(item.amount)}</strong></div>) : <EmptyState title="No receipts yet" text="Attach purchase records from the Receipts section." action={<Button variant="secondary" onClick={() => actions.go('receipts')}>Open receipts</Button>}/>}<Button variant="secondary" onClick={() => actions.go('receipts')}>Manage receipts</Button></section></div><DemoNotice text="Status edits are local and illustrative. A real workshop dashboard needs authenticated, server-persisted updates."/>
  </div>
}
function ProgressSteps({ active }) { const steps = ['Quote approved', 'Advance paid', 'In production', 'Ready to finish']; return <div className="progress-steps">{steps.map((step, index) => <div className={`progress-step ${index <= active ? 'complete' : ''}`} key={step}><span className="progress-node">{index < active ? <Icon name="check" size={12}/> : null}</span><small>{step}</small></div>)}</div> }

function CustomerFlow({ route, quote, orders, loading, actions }) {
  if (route === 'customer/quote') return <CustomerQuote quote={quote} orders={orders} loading={loading} actions={actions}/>
  if (route === 'customer/tracking') return <CustomerTracking quote={quote} orders={orders} loading={loading} actions={actions}/>
  return <CustomerRequest actions={actions}/>
}
function CustomerRequest({ actions }) {
  const [form, setForm] = useState({ description: 'I need a two-door wardrobe in white melamine, 1.20 m wide, 1.80 m tall and 0.55 m deep, with metal handles.', customer: 'Lucia Ramos', email: 'lucia.ramos@example.com' })
  const [submitting, setSubmitting] = useState(false)
  const [validation, setValidation] = useState('')
  const [photoName, setPhotoName] = useState('')
  const [voiceStatus, setVoiceStatus] = useState('Type a description, or tap Speak to use voice input.')
  const startVoiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) { setVoiceStatus('Voice input is unavailable in this browser. You can type your request instead.'); return }
    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.onstart = () => setVoiceStatus('Listening… speak your project details.')
    recognition.onresult = (event) => { setForm((current) => ({ ...current, description: event.results[0][0].transcript })); setVoiceStatus('Voice request added. Review it before continuing.') }
    recognition.onerror = () => setVoiceStatus('Voice input could not start. Check microphone access or type your request.')
    recognition.onend = () => setVoiceStatus((current) => current.startsWith('Listening') ? 'No speech detected. You can try again or type your request.' : current)
    recognition.start()
  }
  const submit = async (event) => {
    event.preventDefault()
    if (form.description.trim().length < 12) { setValidation('Add a little more detail about the piece you need.'); return }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) { setValidation('Enter a valid email address for the invoice.'); return }
    setValidation(''); setSubmitting(true)
    try { await mockApi.createQuote({ ...form, project: 'Two-door melamine wardrobe' }); await actions.refresh(); actions.go('customer/quote') }
    catch { setValidation('The demo quote could not be prepared. Please try again.') }
    finally { setSubmitting(false) }
  }
  return <div className="customer-page"><PageHeading title="What would you like us to make?" description="Describe your piece in your own words. Get a clear estimate to review with the workshop."/><div className="customer-request-grid"><form className="panel request-form" onSubmit={submit}><label className="field-label" htmlFor="project-description">Your request</label><textarea id="project-description" rows="4" required minLength="12" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}/><div className="request-tools"><span className="form-hint" aria-live="polite">{voiceStatus}</span><button className="voice-button" type="button" onClick={startVoiceInput}><Icon name="mic" size={14}/> Speak</button></div><label className="photo-upload"><input type="file" accept="image/png,image/jpeg" onChange={(e) => setPhotoName(e.target.files?.[0]?.name || '')}/><Icon name="upload" size={16}/><span>{photoName || 'Add a reference photo (optional) · JPG or PNG'}</span></label><div className="customer-fields"><label>Full name<input required value={form.customer} onChange={(e) => setForm({ ...form, customer: e.target.value })}/></label><label>Email for your PayPal invoice<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}/></label></div>{validation && <p className="inline-error" role="alert">{validation}</p>}<Button type="submit" disabled={submitting} className="full">{submitting ? 'Preparing your demo estimate…' : 'Get my quote'} <Icon name="arrow" size={16}/></Button><DemoNotice text="This estimate is a fixed example, not an AI-generated or workshop-approved price."/></form>
      <aside className="panel how-panel"><h2>How it works</h2><ol>{[['Describe your piece', 'Share the size, materials and details you know.'], ['Review a clear estimate', 'See an illustrative material and labor breakdown.'], ['Pay a 50% deposit with PayPal', 'Payment is simulated; no charge is made.'], ['Follow every expense', 'The demo can list receipt records from the workshop.'], ['Pay the balance when finished', 'A real final invoice requires backend and PayPal setup.']].map(([title, text], index) => <li key={title}><span>{index + 1}</span><div><strong>{title}</strong><small>{text}</small></div></li>)}</ol></aside></div></div>
}
function CustomerQuote({ quote, orders, loading, actions }) {
  const [busy, setBusy] = useState(false)
  if (loading) return <div className="customer-page"><LoadingState/></div>
  if (!quote) return <div className="customer-page"><EmptyState title="No quote is ready yet" text="Describe the piece you want made to prepare an illustrative estimate." action={<Button onClick={() => actions.go('customer/new')}>Describe your project</Button>}/></div>
  const payDeposit = async () => { setBusy(true); await actions.mutate(() => mockApi.simulatePayment('deposit'), 'Demo only: no PayPal payment was sent and no money was charged.'); setBusy(false); actions.go('customer/tracking') }
  const approve = async () => { setBusy(true); await actions.mutate(() => mockApi.approveQuote(), 'The quote was approved in local demo data.'); setBusy(false) }
  const order = orders.find((item) => item.id === quote.id)
  return <div className="customer-page"><PageHeading title="Your quote is ready" description={`Review the illustrative estimate for ${quote.customer}. Workshop approval and pricing are not connected.`}/><div className="quote-review-grid"><section className="panel quote-breakdown"><div className="quote-title-row"><div><h2>{quote.project}</h2><p>{quote.measurements.width} wide · {quote.measurements.height} tall · {quote.measurements.depth} deep</p></div><span className={`status ${quote.status === 'approved' ? 'status-paid' : 'status-pending'}`}>{quote.status === 'approved' ? 'Approved in demo' : 'Workshop review required'}</span></div><h3 className="field-label">Materials</h3>{quote.items.filter((item) => item.kind === 'material').map((item) => <DataLine key={item.label} label={item.label} value={formatMoney(item.amount)}/>)}<h3 className="field-label labor-label">Labor</h3>{quote.items.filter((item) => item.kind === 'labor').map((item) => <DataLine key={item.label} label={item.label} value={formatMoney(item.amount)}/>)}<div className="quote-total"><span>Estimated total</span><strong>{formatMoney(quote.total)}</strong></div><p className="fine-print">Illustrative demo estimate only. A workshop must review and approve the price before it becomes payable.</p></section>
      <aside className="panel payment-plan"><h2>Payment plan</h2><div className="payment-amount"><span>Today · 50% deposit</span><strong>{formatMoney(quote.deposit)}</strong><small>Example amount for the demo flow.</small></div><div className="payment-amount balance-amount"><span>When finished · balance</span><strong>{formatMoney(quote.balance)}</strong><small>The deposit is subtracted from the example total.</small></div>{quote.paymentDemo ? <Button variant="success" className="full" onClick={() => actions.go('customer/tracking')}>View demo order <Icon name="arrow" size={15}/></Button> : <Button variant="paypal" className="full" disabled={busy || quote.status !== 'approved'} onClick={payDeposit}>{busy ? 'Updating demo…' : quote.status === 'approved' ? `Pay ${formatMoney(quote.deposit)} deposit with PayPal` : 'Waiting for workshop approval'}</Button>}<p className="secure-note">PayPal Sandbox demo only. This prototype does not initiate a payment.</p>{!order && <Button variant="secondary" className="full approve-button" disabled={busy || quote.status === 'approved'} onClick={approve}>{quote.status === 'approved' ? 'Approved in demo' : 'Approve example quote'}</Button>}</aside></div></div>
}
function CustomerTracking({ quote, orders, loading, actions }) {
  if (loading) return <div className="customer-page"><LoadingState/></div>
  const order = quote && orders.find((item) => item.id === quote.id)
  if (!quote || !order) return <div className="customer-page"><EmptyState title="No order to track yet" text="Prepare an estimate first to see the customer tracking flow." action={<Button onClick={() => actions.go('customer/new')}>Start an estimate</Button>}/></div>
  const payBalance = async () => { await actions.mutate(() => mockApi.simulatePayment('balance'), 'Demo only: no final payment was sent and no money was charged.') }
  return <div className="customer-page"><PageHeading title={`${quote.project} is in production`} description={`Order ${order.id} · Deposit received in the local demo. See a sample progress and receipt summary.`}/><section className="panel progress-panel"><ProgressSteps active={Math.min(3, ['quote_sent', 'paid', 'in_progress', 'ready_to_finish', 'delivered'].indexOf(order.status))}/></section><div className="detail-grid tracking-grid"><section className="panel detail-panel"><div className="section-head"><div><h2>Material receipts</h2><p>Sample records uploaded by the workshop.</p></div><span className="status status-paid">{order.receipts.length} records</span></div>{order.receipts.length ? order.receipts.map((item) => <div className="mini-receipt" key={item.id}><span><strong>{item.label}</strong><small>{item.id} · {item.date}</small></span><b>{formatMoney(item.amount)}</b></div>) : <EmptyState title="No receipts added yet" text="Receipt records will appear here when the workshop uploads them."/>}</section><aside className="panel detail-panel"><h2>Your payments</h2><div className="success-callout"><span className="check-dot"><Icon name="check" size={13}/></span><div><strong>{order.paid ? `Deposit of ${formatMoney(order.paid)} · demo record` : 'No payment record'}</strong><small>No PayPal payment has been verified.</small></div></div><DataLine label="Estimate total" value={formatMoney(order.amount)}/><DataLine label="Example balance" value={formatMoney(Math.max(0, order.amount - order.paid))}/><div className="progress-track"><span style={{ width: `${Math.min(100, order.amount ? order.paid / order.amount * 100 : 0)}%` }}/></div>{order.status === 'ready_to_finish' && <Button variant="paypal" className="full" onClick={payBalance}>Simulate balance payment</Button>}<p className="fine-print">The backend must verify PayPal transactions before an order is marked paid.</p></aside></div><DemoNotice text="Order and payment states are local examples only."/></div>
}

export default App

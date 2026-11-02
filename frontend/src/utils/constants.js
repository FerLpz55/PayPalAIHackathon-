export const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'grid' },
  { id: 'orders', label: 'Orders', icon: 'clipboard' },
  { id: 'quotes', label: 'Quotes', icon: 'file' },
  { id: 'receipts', label: 'Receipts', icon: 'receipt' },
  { id: 'accounting', label: 'Accounting', icon: 'chart' },
]

export const STATUS_LABELS = {
  pending: 'Pending',
  quote_sent: 'Quote sent',
  paid: 'Paid',
  in_progress: 'In production',
  ready_to_finish: 'Ready to finish',
  delivered: 'Delivered',
}

export const ORDER_STATUSES = Object.keys(STATUS_LABELS)

// Backend-supported order transitions considered by the demo workflow.
// Manual `paid` updates are omitted, and the demo blocks `delivered` because it
// cannot establish the backend-verified full-payment prerequisite. Legacy demo
// statuses remain display-only.
export const ORDER_STATUS_TRANSITIONS = {
  pending: ['in_progress'],
  paid: ['in_progress'],
  in_progress: ['delivered'],
  delivered: [],
}

export const PROGRESS_STATUSES = ['quote_sent', 'paid', 'in_progress', 'ready_to_finish', 'delivered']

export const PROGRESS_STEPS = ['Quote approved', 'Advance paid', 'In production', 'Ready to finish']

export const ACTIVE_STATUSES = ['pending', 'quote_sent', 'paid', 'in_progress', 'ready_to_finish']

export const TOPBAR_LABELS = {
  dashboard: ['Dashboard', 'Good morning, Alex'],
  orders: ['Orders', 'Your workshop orders'],
  quotes: ['Quotes', 'Review and prepare quotes'],
  receipts: ['Receipts', 'Materials and order receipts'],
  accounting: ['Accounting', 'Your workshop finances'],
  order: ['Orders', 'Order details'],
}

export const HOW_IT_WORKS_STEPS = [
  ['Describe your piece', 'Share the size, materials and details you know, by text or voice.'],
  ['Review a clear estimate', 'See an illustrative material and labor breakdown.'],
  ['Try a simulated 50% deposit', 'No PayPal checkout is started and no charge is made.'],
  ['Review sample receipt entries', 'File names are kept in local demo data only.'],
  ['Pay the balance when finished', 'A real final invoice requires backend and PayPal setup.'],
]

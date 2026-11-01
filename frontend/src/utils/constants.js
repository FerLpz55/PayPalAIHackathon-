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
  ['Pay a 50% deposit with PayPal', 'Payment is simulated; no charge is made.'],
  ['Follow every expense', 'The demo can list receipt records from the workshop.'],
  ['Pay the balance when finished', 'A real final invoice requires backend and PayPal setup.'],
]

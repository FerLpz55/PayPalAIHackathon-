export const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'grid' },
  { id: 'orders', label: 'Orders', icon: 'clipboard' },
  { id: 'quotes', label: 'Quotes', icon: 'file' },
  { id: 'accounting', label: 'Accounting', icon: 'chart' },
]

export const STATUS_LABELS = {
  pending: 'Pending',
  quote_sent: 'Quote sent',
  paid: 'Paid',
  in_progress: 'In production',
  ready_to_finish: 'Ready to finish',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
}

export const ORDER_STATUSES = Object.keys(STATUS_LABELS)

export const ORDER_STATUS_TRANSITIONS = {
  pending: ['in_progress', 'cancelled'],
  paid: ['in_progress', 'cancelled'],
  in_progress: ['delivered', 'cancelled'],
  delivered: [],
  cancelled: [],
}

export const FINANCIAL_STATUS_LABELS = {
  unpaid: 'Unpaid',
  deposit_paid: 'Deposit paid',
  paid: 'Paid in full',
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
  ['Describe your custom piece', 'Share dimensions, preferred woods, and project details by text or voice.'],
  ['AI estimate & market prices', 'Receive an instant breakdown of lumber, hardware, and workshop labor grounded in real merchant rates.'],
  ['Approve & 50% PayPal deposit', 'Lock in workshop scheduling with a secure, verified PayPal advance payment.'],
  ['Track workshop build & delivery', 'Follow live carpentry progress and settle the final balance upon completion.'],
]

// Perfil único del taller mostrado en el portal del cliente y en el panel del taller.
export const WORKSHOP_PROFILE = {
  name: (import.meta.env?.VITE_WORKSHOP_NAME || 'Madera Norte').trim(),
  type: (import.meta.env?.VITE_WORKSHOP_TYPE || 'Carpentry studio').trim(),
}

export const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'grid' },
  { id: 'orders', label: 'Orders', icon: 'clipboard' },
  { id: 'quotes', label: 'Quotes', icon: 'file' },
  { id: 'receipts', label: 'Receipts · DEMO', icon: 'file' },
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

// Keep fixture-only lifecycle labels out of filters that query the backend.
export const REAL_ORDER_STATUS_LABELS = {
  pending: 'Pending',
  paid: 'Paid',
  in_progress: 'In production',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
}

export function getOrderStatusLabels(demoMode) {
  return demoMode ? STATUS_LABELS : REAL_ORDER_STATUS_LABELS
}

export const ORDER_STATUSES = Object.keys(STATUS_LABELS)

export const ORDER_STATUS_TRANSITIONS = {
  pending: ['in_progress', 'cancelled'],
  paid: ['in_progress', 'cancelled'],
  in_progress: ['delivered', 'cancelled'],
  delivered: [],
  cancelled: [],
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

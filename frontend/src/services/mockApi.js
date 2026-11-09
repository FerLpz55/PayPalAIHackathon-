import { ORDER_STATUS_TRANSITIONS } from '../utils/constants.js'

const STORAGE_KEY = 'tallerclaro.demo.v1'

const seedOrders = [
  { id: 'TC-1048', customer: 'Lucia Ramos', email: 'lucia.ramos@example.com', project: 'Two-door melamine wardrobe', amount: 18400, status: 'in_progress', date: '2026-10-21', paid: 9200, spent: 4980, receipts: [{ id: 'R-203', label: 'Melamine boards · 3 sheets', amount: 4200, date: 'Oct 21', state: 'verified' }, { id: 'R-204', label: 'Hinges and handles · 1 set', amount: 780, date: 'Oct 21', state: 'verified' }] },
  { id: 'TC-1047', customer: 'Marco Silva', email: 'marco.silva@example.com', project: 'Dining table · solid pine', amount: 12800, status: 'quote_sent', date: '2026-10-20', paid: 0, spent: 0, receipts: [] },
  { id: 'TC-1046', customer: 'Nora Cruz', email: 'nora.cruz@example.com', project: 'Linen curtains · 4 panels', amount: 6250, status: 'ready_to_finish', date: '2026-10-18', paid: 3125, spent: 0, receipts: [] },
  { id: 'TC-1045', customer: 'Pablo Leon', email: 'pablo.leon@example.com', project: 'Steel garden bench', amount: 9700, status: 'in_progress', date: '2026-10-16', paid: 4850, spent: 0, receipts: [] },
  { id: 'TC-1044', customer: 'Eva Torres', email: 'eva.torres@example.com', project: 'Oak entryway shelves', amount: 5400, status: 'quote_sent', date: '2026-10-14', paid: 0, spent: 0, receipts: [] },
  { id: 'TC-1043', customer: 'Luis Herrera', email: 'luis.herrera@example.com', project: 'Kitchen island · birch', amount: 22100, status: 'quote_sent', date: '2026-10-12', paid: 0, spent: 0, receipts: [] },
  { id: 'TC-1042', customer: 'Sofia Vega', email: 'sofia.vega@example.com', project: 'Walnut coffee table', amount: 10900, status: 'in_progress', date: '2026-10-10', paid: 3600, spent: 0, receipts: [] },
  { id: 'TC-1041', customer: 'Diego Mora', email: 'diego.mora@example.com', project: 'Pine bookcase', amount: 7900, status: 'ready_to_finish', date: '2026-10-08', paid: 4075, spent: 0, receipts: [] },
]

function readStore() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY))
    if (saved?.orders && Array.isArray(saved.orders)) return saved
  } catch { /* Ignore invalid local demo data and restore the fixtures. */ }
  return { orders: seedOrders, quote: null }
}

let state = readStore()
const persist = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
const delay = (value) => new Promise((resolve) => window.setTimeout(() => resolve(structuredClone(value)), 220))

export const mockApi = {
  async listOrders() { return delay(state.orders) },
  async getQuote() { return delay(state.quote) },
  async createQuote(input) {
    const quote = {
      id: `TC-${1050 + state.orders.filter((order) => Number(order.id.slice(3)) >= 1050).length}`,
      customer: input.customer.trim(), email: input.email.trim(), description: input.description.trim(),
      project: input.project || 'Custom wardrobe', total: 1200, deposit: 600, balance: 600,
      measurements: { width: '1.20 m', height: '1.80 m', depth: '0.55 m' },
      items: [
        { label: 'Melamine boards 18 mm · 3 sheets', amount: 360, kind: 'material' },
        { label: 'Edging · 12 m', amount: 40, kind: 'material' },
        { label: 'Hinges and handles · 1 set', amount: 70, kind: 'material' },
        { label: 'Fasteners and supplies · 1 lot', amount: 30, kind: 'material' },
        { label: 'Cutting, assembly and finish · 12 hours', amount: 700, kind: 'labor' },
      ], status: 'draft', createdAt: new Date().toISOString(), isDemo: true,
    }
    state.quote = quote
    persist()
    return delay(quote)
  },
  async approveQuote() {
    if (!state.quote) throw new Error('Create a quote before approving it.')
    state.quote = { ...state.quote, status: 'approved' }
    if (!state.orders.some((order) => order.id === state.quote.id)) {
      state.orders = [{ id: state.quote.id, customer: state.quote.customer, email: state.quote.email, project: state.quote.project, amount: state.quote.total, status: 'quote_sent', date: new Date().toISOString().slice(0, 10), paid: 0, spent: 0, receipts: [] }, ...state.orders]
    }
    persist()
    return delay(state.quote)
  },
  async simulatePayment(kind = 'deposit') {
    if (!state.quote) throw new Error('There is no quote to pay.')
    state.quote = { ...state.quote, paymentDemo: kind, status: kind === 'deposit' ? 'in_progress' : 'paid' }
    const order = state.orders.find((item) => item.id === state.quote.id)
    if (order) {
      order.paid = kind === 'deposit' ? state.quote.deposit : state.quote.total
      order.status = kind === 'deposit' ? 'in_progress' : 'paid'
    }
    persist()
    return delay(state.quote)
  },
  async updateStatus(id, status) {
    const order = state.orders.find((item) => item.id === id || String(item.orderId) === String(id))
    if (!order) throw new Error('This order could not be found.')
    if (status === 'deleted') {
      state.orders = state.orders.filter((item) => item.id !== order.id)
      persist()
      return delay({ ...order, status: 'deleted' })
    }
    if (status === 'delivered') {
      throw new Error('Delivery requires backend-verified full payment and is unavailable in the demo.')
    }
    if (status !== 'cancelled' && !ORDER_STATUS_TRANSITIONS[order.status]?.includes(status)) {
      throw new Error(`The demo does not allow changing ${order.status} to ${status}.`)
    }
    order.status = status
    persist()
    return delay(order)
  },
  async cancelOrder(id) {
    return this.updateStatus(id, 'cancelled')
  },
  async deleteOrder(id) {
    return this.updateStatus(id, 'deleted')
  },
  async recordDemoCompletionNote(id) {
    const order = state.orders.find((item) => item.id === id)
    if (!order) throw new Error('This order could not be found.')
    if (order.status !== 'ready_to_finish') {
      throw new Error('A demo completion note is available only for a ready-to-finish sample order.')
    }
    if (order.demoCompletionNoteAt) throw new Error('A demo completion note already exists for this order.')
    order.demoCompletionNoteAt = new Date().toISOString()
    persist()
    return delay(order)
  },
  async askAccountingAssistant(question) {
    const orders = state.orders
    const collected = orders.reduce((sum, order) => sum + Number(order.paid || 0), 0)
    const contracted = orders.reduce((sum, order) => sum + Number(order.amount || 0), 0)
    const pending = orders
      .filter((order) => order.status !== 'delivered')
      .reduce((sum, order) => sum + Math.max(0, Number(order.amount || 0) - Number(order.paid || 0)), 0)
    const awaitingDeposit = orders.filter((order) => !Number(order.paid)).length
    const summary = {
      currency: 'USD',
      ordersCount: orders.length,
      awaitingDeposit,
      totalContracted: contracted,
      collectedTotal: collected,
      pendingToCollect: pending,
    }
    const usd = (value) => `$${Math.round(value).toLocaleString('en-US')}`
    const spanish = /[¿áéíóúñ]|\b(cu[aá]nto|gan[eé]|cobr|debe|pedido)/i.test(question)
    const answer = spanish
      ? `Respuesta de demostración: en tus ${orders.length} pedidos de ejemplo ya cobraste ${usd(collected)} y te falta cobrar ${usd(pending)}. ${awaitingDeposit} pedidos aún esperan su anticipo. Como los gastos de materiales no se registran, no puedo calcular tu ganancia.`
      : `Demo answer: across your ${orders.length} sample orders you have collected ${usd(collected)} and still have ${usd(pending)} to collect. ${awaitingDeposit} orders are still waiting for their deposit. Material costs are not recorded, so I cannot calculate profit.`
    return delay({ question, answer, summary, isDemo: true })
  },
  async addReceipt(id, file) {
    const order = state.orders.find((item) => item.id === id)
    if (!order) throw new Error('This order could not be found.')
    const receipt = { id: `R-${205 + order.receipts.length}`, label: file.name, amount: 0, date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), state: 'pending' }
    order.receipts = [...order.receipts, receipt]
    persist()
    return delay(receipt)
  },
}

export const resetDemoData = () => { localStorage.removeItem(STORAGE_KEY); state = { orders: seedOrders, quote: null } }

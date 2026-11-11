import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearWorkshopSession,
  getWorkshopSession,
  saveWorkshopSession,
  clearPendingPayment,
  clearSession,
  discardPendingPayment,
  getCompletedPayment,
  getPendingPayment,
  getSession,
  readPendingPayment,
  savePendingPayment,
  saveSession,
} from '../sessionStore.js'

describe('sessionStore', () => {
  let mockStore = {}

  beforeEach(() => {
    mockStore = {}
    globalThis.sessionStorage = {
      getItem(key) {
        return Object.prototype.hasOwnProperty.call(mockStore, key) ? mockStore[key] : null
      },
      setItem(key, value) {
        mockStore[key] = String(value)
      },
      removeItem(key) {
        delete mockStore[key]
      },
      clear() {
        mockStore = {}
      },
    }
  })

  it('manages session lifecycle (save, get, clear)', () => {
    expect(getSession()).toEqual({})
    saveSession({ customerToken: 'tok-123', customerName: 'Ana' })
    expect(getSession()).toEqual({ customerToken: 'tok-123', customerName: 'Ana' })

    saveSession({ customerEmail: 'ana@example.com' })
    expect(getSession()).toEqual({
      customerToken: 'tok-123',
      customerName: 'Ana',
      customerEmail: 'ana@example.com',
    })

    clearSession()
    expect(getSession()).toEqual({})
  })

  it('manages pending payments and transitions to completed', () => {
    expect(readPendingPayment()).toBeNull()

    const payment = {
      paymentId: 'pay-456',
      orderId: 1048,
      type: 'deposit',
      amount: '500.00',
    }

    savePendingPayment(payment)
    expect(readPendingPayment()).toEqual(payment)
    expect(getPendingPayment(1048, 'deposit')).toEqual(payment)
    expect(getPendingPayment(1048, 'balance')).toBeNull()

    // Clear pending transitions it to completed
    clearPendingPayment('pay-456')
    expect(readPendingPayment()).toBeNull()

    const completed = getCompletedPayment(1048, 'deposit')
    expect(completed).toEqual({ orderId: 1048, type: 'deposit', paymentId: 'pay-456' })
  })

  it('discards a pending payment without marking it completed', () => {
    savePendingPayment({ paymentId: 'pay-789', orderId: 2000, type: 'balance' })
    discardPendingPayment('pay-789')

    expect(readPendingPayment()).toBeNull()
    expect(getCompletedPayment(2000, 'balance')).toBeNull()
  })
})


describe('workshop session metadata', () => {
  beforeEach(() => {
    let store = {}
    globalThis.sessionStorage = {
      getItem: (key) => (Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null),
      setItem: (key, value) => { store[key] = String(value) },
      removeItem: (key) => { delete store[key] },
      clear: () => { store = {} },
    }
  })

  it('stores and clears the workshop session without touching the customer token', () => {
    saveSession({ customerToken: 'cust-1' })
    saveWorkshopSession({ authenticated: true, username: 'taller', csrfToken: 'csrf' })

    expect(getWorkshopSession()).toMatchObject({ username: 'taller', csrfToken: 'csrf' })
    expect(getSession().customerToken).toBe('cust-1')

    clearWorkshopSession()
    expect(getWorkshopSession()).toBeNull()
    expect(getSession().customerToken).toBe('cust-1')
  })
})

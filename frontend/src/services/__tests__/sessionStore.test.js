import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearPendingPayment,
  clearSession,
  discardPendingPayment,
  getCompletedPayment,
  getPendingPayment,
  getSession,
  clearWorkshopCredentials,
  getWorkshopCredentials,
  readPendingPayment,
  savePendingPayment,
  saveSession,
  setWorkshopCredentials,
} from '../sessionStore.js'

describe('sessionStore', () => {
  let mockStore = {}

  beforeEach(() => {
    mockStore = {}
    clearWorkshopCredentials()
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

  it('keeps workshop Basic credentials in memory only', () => {
    const authorization = setWorkshopCredentials('workshop-user', 'fake-password')

    expect(getWorkshopCredentials()).toBe(authorization)
    expect(atob(authorization)).toBe('workshop-user:fake-password')
    expect(mockStore).toEqual({})

    clearWorkshopCredentials()
    expect(getWorkshopCredentials()).toBeNull()
  })

  it('rejects an invalid Basic username or empty password', () => {
    expect(() => setWorkshopCredentials('user:name', 'fake-password')).toThrow()
    expect(() => setWorkshopCredentials('workshop-user', '')).toThrow()
    expect(getWorkshopCredentials()).toBeNull()
  })

  it('does not reuse workshop credentials stored in sessionStorage', () => {
    mockStore['tallerclaro.session.v1'] = JSON.stringify({ workshopCredentials: 'c3RhbGU=' })
    expect(getWorkshopCredentials()).toBeNull()
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

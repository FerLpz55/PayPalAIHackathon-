import { describe, expect, it } from 'vitest'
import {
  adaptQuoteResponse,
  adaptOrderResponse,
  adaptAccountingSummary,
  parseNumericId,
  extractMeasurements,
  getRemainingBalance,
} from '../adapters.js'

describe('parseNumericId', () => {
  it('parses numeric strings and numbers', () => {
    expect(parseNumericId(1048)).toBe(1048)
    expect(parseNumericId('1048')).toBe(1048)
    expect(parseNumericId('TC-1048')).toBe(1048)
  })

  it('handles null and undefined', () => {
    expect(parseNumericId(null)).toBeNull()
    expect(parseNumericId(undefined)).toBeNull()
  })
})

describe('extractMeasurements', () => {
  it('extracts width, height, and depth from text', () => {
    const text = 'Ropero de 1.50 m de ancho, 2.10 m de alto y 0.60 m de profundidad'
    const result = extractMeasurements(text)
    expect(result.width).toBe('1.50 m')
    expect(result.height).toBe('2.10 m')
    expect(result.depth).toBe('0.60 m')
  })

  it('extracts dimensions described in English', () => {
    const result = extractMeasurements('Desk 120 cm wide, 75 cm tall, and 55 cm deep')
    expect(result.width).toBe('120 cm')
    expect(result.height).toBe('75 cm')
    expect(result.depth).toBe('55 cm')
  })

  it('leaves unreported dimensions blank instead of inventing defaults', () => {
    const result = extractMeasurements('')
    expect(result.width).toBeNull()
    expect(result.height).toBeNull()
    expect(result.depth).toBeNull()
  })
})

describe('adaptQuoteResponse', () => {
  it('normalizes amounts and does not infer missing deposit or balance values', () => {
    const raw = {
      id: 55,
      code: 'TC-55',
      total: 1200,
      customer_name: 'Carlos Rivera',
      customer_email: 'carlos@example.com',
      status: 'pending_review',
      items: [
        { id: 1, description: 'Madera de pino', type: 'material', amount: 400 },
        { id: 2, description: 'Mano de obra', type: 'labor', amount: 800 },
      ],
    }

    const adapted = adaptQuoteResponse(raw)
    expect(adapted.numericId).toBe(55)
    expect(adapted.total).toBe(1200)
    expect(adapted.deposit).toBeNull()
    expect(adapted.balance).toBeNull()
    expect(adapted.items).toHaveLength(2)
    expect(adapted.items[0].kind).toBe('material')
    expect(adapted.items[1].kind).toBe('labor')
  })

  it('keeps blank and malformed totals unknown', () => {
    expect(adaptQuoteResponse({ id: 56, status: 'draft', total: '', items: [] }).total).toBeNull()
    expect(adaptQuoteResponse({ id: 57, status: 'draft', total: 'not-a-number', items: [] }).total).toBeNull()
  })

  it('returns null for an empty payload', () => {
    expect(adaptQuoteResponse(null)).toBeNull()
  })
})

describe('adaptOrderResponse', () => {
  it('normalizes order identifiers without inferring payment splits', () => {
    const adapted = adaptOrderResponse({
      id: 77,
      code: 'TC-77',
      quote_id: 12,
      total: 900,
      remaining_balance: 450,
      customer_name: 'Ana Ruiz',
    })

    expect(adapted.id).toBe('TC-77')
    expect(adapted.orderId).toBe(77)
    expect(adapted.quoteId).toBe(12)
    expect(adapted.deposit).toBeNull()
    expect(adapted.remainingBalance).toBe(450)
  })

  it('derives a remaining balance only when total and paid amounts are known', () => {
    expect(getRemainingBalance({ amount: 1000, paid: 350 })).toBe(650)
    expect(getRemainingBalance({ amount: 1000, paid: 1200 })).toBe(0)
    expect(getRemainingBalance({ amount: 1000, paid: null })).toBeNull()
  })
})

describe('adaptAccountingSummary', () => {
  it('normalizes financial summary fields', () => {
    const summary = adaptAccountingSummary({
      currency: 'USD',
      orders_count: 5,
      orders_awaiting_deposit: 2,
      total_contracted: 3500.5,
      collected_total: 1750.25,
      pending_to_collect: 1750.25,
    })

    expect(summary.currency).toBe('USD')
    expect(summary.ordersCount).toBe(5)
    expect(summary.awaitingDeposit).toBe(2)
    expect(summary.totalContracted).toBe(3500.5)
    expect(summary.collectedTotal).toBe(1750.25)
    expect(summary.pendingToCollect).toBe(1750.25)
  })

  it('keeps absent financial values unknown', () => {
    const summary = adaptAccountingSummary()
    expect(summary.currency).toBe('USD')
    expect(summary.ordersCount).toBeNull()
    expect(summary.totalContracted).toBeNull()
  })
})


describe('adaptOrderResponse financial status', () => {
  it('preserves the backend financial_status', () => {
    const order = adaptOrderResponse({
      id: 4,
      quote_id: 2,
      total: 1000,
      deposit_amount: 500,
      balance_amount: 500,
      paid_amount: 500,
      status: 'in_progress',
      financial_status: 'deposit_paid',
    })

    expect(order.financialStatus).toBe('deposit_paid')
    expect(order.paid).toBe(500)
  })

  it('derives a value only when the backend omits financial_status', () => {
    expect(adaptOrderResponse({ id: 1, total: 100, paid_amount: 0 }).financialStatus).toBe('unpaid')
    expect(adaptOrderResponse({ id: 2, total: 100, paid_amount: 50 }).financialStatus).toBe('deposit_paid')
    expect(adaptOrderResponse({ id: 3, total: 100, paid_amount: 100 }).financialStatus).toBe('paid')
  })
})

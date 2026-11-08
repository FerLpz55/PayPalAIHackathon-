import { describe, expect, it } from 'vitest'
import {
  adaptQuoteResponse,
  adaptOrderResponse,
  adaptAccountingSummary,
  parseNumericId,
  extractMeasurements,
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

  it('provides sensible defaults when text is empty', () => {
    const result = extractMeasurements('')
    expect(result.width).toBe('1.20 m')
    expect(result.height).toBe('1.80 m')
    expect(result.depth).toBe('0.55 m')
  })
})

describe('adaptQuoteResponse', () => {
  it('normalizes total, 50% deposit and remaining balance', () => {
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
    expect(adapted.deposit).toBe(600)
    expect(adapted.balance).toBe(600)
    expect(adapted.items).toHaveLength(2)
    expect(adapted.items[0].kind).toBe('material')
    expect(adapted.items[1].kind).toBe('labor')
  })

  it('returns null for an empty payload', () => {
    expect(adaptQuoteResponse(null)).toBeNull()
  })
})

describe('adaptOrderResponse', () => {
  it('normalizes order identifiers and balances', () => {
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
    expect(adapted.deposit).toBe(450)
    expect(adapted.remainingBalance).toBe(450)
  })
})

describe('adaptAccountingSummary', () => {
  it('normalizes financial summary fields with defaults', () => {
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

  it('handles empty input gracefully', () => {
    const summary = adaptAccountingSummary()
    expect(summary.currency).toBe('USD')
    expect(summary.ordersCount).toBe(0)
    expect(summary.totalContracted).toBe(0)
  })
})

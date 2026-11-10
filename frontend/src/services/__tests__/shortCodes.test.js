import { describe, expect, it } from 'vitest'
import {
  adaptOrderResponse,
  adaptQuoteResponse,
  formatMeasurements,
  shortCodeForQuote,
} from '../adapters.js'

describe('short order codes', () => {
  it('derives TC-(1000 + quote id)', () => {
    expect(shortCodeForQuote(48)).toBe('TC-1048')
    expect(shortCodeForQuote(null)).toBeNull()
  })

  it('shows the backend short code as-is', () => {
    expect(adaptOrderResponse({ id: '3', quote_id: '48', code: 'TC-1048' }).id).toBe('TC-1048')
  })

  it('replaces legacy UUID codes with the short code', () => {
    const order = adaptOrderResponse({ id: '9', quote_id: '5', code: 'TC-cf9dfb70481a454380425ac266fb770e' })
    expect(order.id).toBe('TC-1005')
    expect(order.orderId).toBe(9)
  })

  it('gives the quote the same code as its order', () => {
    const quote = adaptQuoteResponse({ id: '5', request: 'Mesa', status: 'draft' })
    expect(quote.id).toBe('TC-1005')
    expect(quote.numericId).toBe(5)
  })
})

describe('formatMeasurements', () => {
  it('omits measurements that were not detected', () => {
    expect(formatMeasurements({ width: null, height: null, depth: null })).toBe('')
    expect(formatMeasurements({ width: '1.20 m', height: null, depth: '0.55 m' })).toBe('1.20 m wide · 0.55 m deep')
  })
})

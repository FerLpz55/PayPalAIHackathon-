import { describe, expect, it } from 'vitest'
import { getOrderStatusLabels } from '../constants.js'

describe('order status filters', () => {
  it('keeps backend filters to the current API order statuses', () => {
    expect(Object.keys(getOrderStatusLabels(false))).toEqual([
      'pending',
      'paid',
      'in_progress',
      'delivered',
      'cancelled',
    ])
  })

  it('preserves fixture-only states in the explicit demo mode', () => {
    const demoStatuses = Object.keys(getOrderStatusLabels(true))
    expect(demoStatuses).toContain('quote_sent')
    expect(demoStatuses).toContain('ready_to_finish')
  })
})

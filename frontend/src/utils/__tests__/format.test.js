import { describe, expect, it } from 'vitest'
import { formatMoney } from '../format.js'

describe('formatMoney', () => {
  it('preserves a known zero amount', () => {
    expect(formatMoney(0)).toBe('$0')
  })

  it('does not display missing or invalid amounts as zero', () => {
    expect(formatMoney(null)).toBe('—')
    expect(formatMoney(undefined)).toBe('—')
    expect(formatMoney('   ')).toBe('—')
    expect(formatMoney(Number.NaN)).toBe('—')
  })
})

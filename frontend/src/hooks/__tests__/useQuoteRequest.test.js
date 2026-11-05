import { describe, expect, it } from 'vitest'
import { deriveProjectTitle } from '../useQuoteRequest.js'

describe('deriveProjectTitle', () => {
  it('uses the first sentence of the request', () => {
    expect(deriveProjectTitle('Two-door melamine wardrobe. Needs soft-close hinges.')).toBe('Two-door melamine wardrobe')
  })

  it('does not truncate decimal measurements as sentences', () => {
    expect(deriveProjectTitle('Wardrobe 1.50 m wide.')).toBe('Wardrobe 1.50 m wide')
  })

  it('caps long descriptions with an ellipsis', () => {
    const title = deriveProjectTitle('A'.repeat(80))
    expect(title).toHaveLength(48)
    expect(title.endsWith('…')).toBe(true)
  })

  it('falls back when the description is empty', () => {
    expect(deriveProjectTitle('   ')).toBe('Custom woodwork project')
  })
})

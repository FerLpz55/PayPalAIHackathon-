import { describe, expect, it } from 'vitest'
import { isSafePayPalUrl } from '../security.js'

describe('isSafePayPalUrl', () => {
  it('accepts legitimate PayPal Sandbox URLs', () => {
    expect(isSafePayPalUrl('https://sandbox.paypal.com/checkoutnow?token=123')).toBe(true)
    expect(isSafePayPalUrl('https://www.sandbox.paypal.com/checkoutnow?token=456')).toBe(true)
  })

  it('accepts legitimate PayPal Live URLs', () => {
    expect(isSafePayPalUrl('https://www.paypal.com/checkoutnow?token=789')).toBe(true)
    expect(isSafePayPalUrl('https://paypal.com/checkoutnow?token=012')).toBe(true)
  })

  it('rejects non-HTTPS schemes', () => {
    expect(isSafePayPalUrl('http://sandbox.paypal.com/checkoutnow')).toBe(false)
    expect(isSafePayPalUrl('javascript:alert(1)')).toBe(false)
    expect(isSafePayPalUrl('data:text/html,<script>')).toBe(false)
  })

  it('rejects phishing or spoofed subdomains', () => {
    expect(isSafePayPalUrl('https://sandbox.paypal.com.attacker.com/fake')).toBe(false)
    expect(isSafePayPalUrl('https://evilpaypal.com')).toBe(false)
    expect(isSafePayPalUrl('https://notpaypal.com/?ref=sandbox.paypal.com')).toBe(false)
  })

  it('handles null, undefined or empty input safely', () => {
    expect(isSafePayPalUrl(null)).toBe(false)
    expect(isSafePayPalUrl(undefined)).toBe(false)
    expect(isSafePayPalUrl('')).toBe(false)
  })
})

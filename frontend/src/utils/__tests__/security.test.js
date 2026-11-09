import { describe, expect, it } from 'vitest'
import { isSafePayPalUrl, isSafeExternalUrl } from '../security.js'

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

describe('isSafeExternalUrl', () => {
  it('accepts valid https and http URLs', () => {
    expect(isSafeExternalUrl('https://www.homedepot.com/p/123')).toBe(true)
    expect(isSafeExternalUrl('http://example.com/product')).toBe(true)
  })

  it('rejects dangerous schemes like javascript: or data:', () => {
    expect(isSafeExternalUrl('javascript:alert(1)')).toBe(false)
    expect(isSafeExternalUrl('data:text/html;base64,PHNjcmlwdD4=')).toBe(false)
    expect(isSafeExternalUrl('vbscript:msgbox')).toBe(false)
  })

  it('handles invalid or empty inputs safely', () => {
    expect(isSafeExternalUrl(null)).toBe(false)
    expect(isSafeExternalUrl(undefined)).toBe(false)
    expect(isSafeExternalUrl('')).toBe(false)
    expect(isSafeExternalUrl('not-a-valid-url')).toBe(false)
  })
})

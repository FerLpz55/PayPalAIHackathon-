import { expect, test } from '@playwright/test'

const API = '**://127.0.0.1:8000/api/**'

function quote(overrides = {}) {
  return {
    id: '1',
    customer_id: '10',
    carpenter_id: '1',
    request: 'Solid oak dining table 1.80m x 0.90m',
    description: 'Solid oak dining table',
    items: [
      { id: 'i1', type: 'material', description: 'Oak boards', unit: 'sheet', quantity: 3, unit_amount: 100, amount: 300 },
      { id: 'i2', type: 'labor', description: 'Workshop labor', unit: 'hour', quantity: 10, unit_amount: 70, amount: 700 },
    ],
    currency: 'USD',
    total: 1000,
    deposit_amount: 500,
    balance_amount: 500,
    status: 'draft',
    assumptions: [],
    missing_info: [],
    suggested_products: [],
    created_at: '2026-11-09T10:00:00Z',
    ...overrides,
  }
}

function order(overrides = {}) {
  return {
    id: '4',
    quote_id: '1',
    code: 'TC-1048',
    total: 1000,
    deposit_amount: 500,
    balance_amount: 500,
    currency: 'USD',
    status: 'pending',
    financial_status: 'unpaid',
    customer_name: 'Ana Torres',
    customer_email: 'ana@example.com',
    project_request: 'Solid oak dining table',
    created_at: '2026-11-09T10:00:00Z',
    payments: [],
    ...overrides,
  }
}

test('customer links recover the quote, approve it and reconcile a PayPal payment', async ({ page }) => {
  let approved = false
  let paid = false

  await page.route(API, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()
    const json = (status, body) => route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(body),
    })

    if (path === '/api/customer/context' && method === 'GET') {
      return json(200, {
        quote: quote({ status: approved ? 'approved' : 'draft' }),
        order: approved ? order({ financial_status: paid ? 'deposit_paid' : 'unpaid' }) : null,
        payments: paid
          ? [{ id: '9', order_id: '4', type: 'deposit', amount: 500, currency: 'USD', status: 'completed', paypal_order_id: 'PP-1', paypal_capture_id: 'CAP-1' }]
          : [],
      })
    }
    if (path === '/api/quotes/1/approve' && method === 'POST') {
      approved = true
      return json(200, order())
    }
    if (path === '/api/quotes/1' && method === 'GET') {
      return json(200, quote({ status: approved ? 'approved' : 'draft' }))
    }
    if (path === '/api/orders/4/payments' && method === 'POST') {
      return json(200, {
        payment_id: '9',
        paypal_order_id: 'PP-1',
        amount: 500,
        currency: 'USD',
        approval_url: 'https://sandbox.paypal.com/checkoutnow?token=PP-1',
      })
    }
    if (path === '/api/payments/9' && method === 'GET') {
      return json(200, {
        id: '9', order_id: '4', type: 'deposit', amount: 500, currency: 'USD',
        status: paid ? 'completed' : 'pending', paypal_order_id: 'PP-1', paypal_capture_id: paid ? 'CAP-1' : null,
      })
    }
    if (path === '/api/payments/9/sync' && method === 'POST') {
      paid = true
      return json(200, {
        id: '9', order_id: '4', type: 'deposit', amount: 500, currency: 'USD',
        status: 'completed', paypal_order_id: 'PP-1', paypal_capture_id: 'CAP-1',
      })
    }
    if (path === '/api/orders/4' && method === 'GET') {
      return json(200, order({ financial_status: paid ? 'deposit_paid' : 'unpaid' }))
    }
    return json(404, { code: 'NOT_FOUND', message: `Unexpected request ${method} ${path}` })
  })

  await page.goto('/#/customer/quote?token=e2e-customer-token')

  // El token se adopta desde el enlace y desaparece de la URL.
  await expect(page).toHaveURL(/#\/customer\/quote$/)
  await expect(page.getByRole('heading', { name: 'Your quote is ready' })).toBeVisible()
  await expect(page.getByText('Solid oak dining table').first()).toBeVisible()

  await page.getByRole('button', { name: 'Approve Quote & Proceed to Deposit' }).click()

  await expect(page.getByRole('heading', { name: 'Pay deposit with PayPal' })).toBeVisible()
  await page.getByRole('button', { name: 'Start PayPal Checkout' }).click()

  await expect(page.getByRole('button', { name: /1\. Open PayPal Checkout/ })).toBeVisible()
  await page.getByRole('button', { name: /2\. Verify & Confirm Payment/ }).click()

  await expect(page.getByText('Payment verified & confirmed by workshop.')).toBeVisible()
  await expect(page.getByText('Deposit paid')).toBeVisible()
})

test('workshop routes require a cookie session and sign out returns to the login gate', async ({ page }) => {
  let authenticated = false

  await page.route(API, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()
    const json = (status, body) => route.fulfill({
      status: authenticated || path === '/api/auth/login' ? status : 401,
      contentType: 'application/json',
      body: JSON.stringify(authenticated || path === '/api/auth/login' ? body : { detail: 'Workshop session required' }),
    })

    if (path === '/api/auth/session' && method === 'GET') {
      return json(200, {
        authenticated: true, carpenter_id: 1, username: 'taller', csrf_token: 'csrf-e2e',
        idle_timeout_seconds: 1800, absolute_timeout_seconds: 28800,
      })
    }
    if (path === '/api/auth/login' && method === 'POST') {
      authenticated = true
      return json(200, {
        authenticated: true, carpenter_id: 1, username: 'taller', csrf_token: 'csrf-e2e',
        idle_timeout_seconds: 1800, absolute_timeout_seconds: 28800,
      })
    }
    if (path === '/api/orders' && method === 'GET') {
      return json(200, { orders: [], total: 0, limit: 20, offset: 0 })
    }
    if (path === '/api/auth/logout' && method === 'POST') {
      authenticated = false
      return route.fulfill({ status: 204 })
    }
    return json(200, {})
  })

  await page.goto('/#/dashboard')

  await expect(page.getByRole('heading', { name: 'Workshop sign in' })).toBeVisible()
  await page.getByLabel('Username').fill('taller')
  await page.getByLabel('Password').fill('demo-password')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page.getByRole('heading', { name: 'Workshop dashboard' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Sign out of the workshop session' })).toBeVisible()

  await page.getByRole('button', { name: 'Sign out of the workshop session' }).click()

  await expect(page.getByRole('heading', { name: 'Workshop sign in' })).toBeVisible()
})

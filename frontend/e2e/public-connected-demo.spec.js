import { expect, test } from '@playwright/test'

const API = '**://127.0.0.1:8000/api/**'

function quote(overrides = {}) {
  return {
    id: '1',
    customer_id: '10',
    carpenter_id: '1',
    request: 'Solid oak dining table 1.80m x 0.90m',
    description: 'AI-generated solid oak dining table estimate',
    items: [
      { id: 'i1', type: 'material', description: 'AI-selected oak boards', unit: 'board', quantity: 3, unit_amount: 100, amount: 300 },
      { id: 'i2', type: 'labor', description: 'Workshop labor', unit: 'hour', quantity: 10, unit_amount: 70, amount: 700 },
    ],
    currency: 'USD',
    total: 1000,
    deposit_amount: 500,
    balance_amount: 500,
    status: 'pending_review',
    assumptions: ['Clear finish and standard joinery'],
    missing_info: [],
    suggested_products: [
      {
        id: 'channel3-oak',
        title: 'Channel3 kiln-dried solid oak board',
        price_usd: 99.95,
        source: 'Channel3 Merchant',
        url: 'https://example.com/channel3-oak',
        image_url: null,
      },
    ],
    created_at: '2026-11-11T10:00:00Z',
    ...overrides,
  }
}

function order() {
  return {
    id: '4',
    quote_id: '1',
    code: 'TC-1001',
    total: 1000,
    deposit_amount: 500,
    balance_amount: 500,
    paid_amount: 0,
    currency: 'USD',
    status: 'pending',
    financial_status: 'unpaid',
    customer_name: 'Ana Torres',
    customer_email: 'ana@example.com',
    project_request: 'Solid oak dining table',
    created_at: '2026-11-11T10:00:00Z',
    payments: [],
  }
}

async function installConnectedBackend(page) {
  const state = {
    generated: false,
    approved: false,
    workshopSessionRequests: 0,
  }

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

    if (path === '/api/auth/session' && method === 'GET') {
      state.workshopSessionRequests += 1
      return json(401, { detail: 'Workshop session required' })
    }
    if (path === '/api/quotes' && method === 'POST') {
      return json(201, quote({ status: 'draft', items: [], total: null, deposit_amount: null, balance_amount: null, customer_token: 'customer-token-1' }))
    }
    if (path === '/api/quotes/1/generate' && method === 'POST') {
      state.generated = true
      return json(200, quote())
    }
    if (path === '/api/quotes/1' && method === 'GET') {
      if (!state.generated) return json(409, { message: 'AI generation must complete first' })
      return json(200, quote({ status: state.approved ? 'approved' : 'pending_review' }))
    }
    if (path === '/api/customer/context' && method === 'GET') {
      if (!state.generated) return json(409, { message: 'AI generation must complete first' })
      return json(200, {
        quote: quote({ status: state.approved ? 'approved' : 'pending_review' }),
        order: state.approved ? order() : null,
        payments: [],
      })
    }
    if (path === '/api/quotes/1/approve' && method === 'POST') {
      state.approved = true
      return json(200, order())
    }
    if (path === '/api/orders/4/payments' && method === 'POST') {
      return json(200, {
        payment_id: '9',
        paypal_order_id: 'PAYPAL-SANDBOX-1',
        amount: 500,
        currency: 'USD',
        approval_url: 'https://sandbox.paypal.com/checkoutnow?token=PAYPAL-SANDBOX-1',
      })
    }
    return json(404, { code: 'NOT_FOUND', message: `Unexpected request ${method} ${path}` })
  })

  return state
}

test('the root opens the public backend-connected AI, Channel3, and PayPal journey', async ({ page }) => {
  const state = await installConnectedBackend(page)

  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'What would you like us to make?' })).toBeVisible()
  await page.getByLabel('Your request').fill('Solid oak dining table 1.80m x 0.90m with clear finish')
  await page.getByLabel('Full name').fill('Ana Torres')
  await page.getByLabel('Email for your quote').fill('ana@example.com')
  await page.getByRole('button', { name: /Generate instant estimate/ }).click()

  await expect(page.getByRole('heading', { name: 'Quote review' })).toBeVisible()
  await expect(page.getByText('AI-selected oak boards')).toBeVisible()
  await expect(page.getByText('Channel3 kiln-dried solid oak board')).toBeVisible()

  await page.getByRole('button', { name: 'Approve quote' }).click()
  await expect(page.getByRole('heading', { name: 'Pay deposit with PayPal' })).toBeVisible()
  await page.getByRole('button', { name: 'Start PayPal Checkout' }).click()
  await expect(page.getByRole('button', { name: /Open PayPal Checkout/ })).toBeVisible()
  expect(state.workshopSessionRequests).toBe(0)
})

test('an explicit workshop dashboard route remains protected', async ({ page }) => {
  const state = await installConnectedBackend(page)

  await page.goto('/#/dashboard')

  await expect(page.getByRole('heading', { name: 'Workshop sign in' })).toBeVisible()
  expect(state.workshopSessionRequests).toBeGreaterThan(0)
})

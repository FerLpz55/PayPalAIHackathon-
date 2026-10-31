const API_URL = import.meta.env.VITE_API_URL

export async function requestQuote({ description, customerName, customerEmail }) {
  if (!API_URL) {
    await new Promise((resolve) => setTimeout(resolve, 800))
    return { id: 'demo-quote', status: 'draft' }
  }

  const response = await fetch(`${API_URL}/quotes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      description,
      customer_name: customerName,
      customer_email: customerEmail,
    }),
  })

  if (!response.ok) {
    throw new Error('We could not create your quote. Please try again.')
  }

  return response.json()
}

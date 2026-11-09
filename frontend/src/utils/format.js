export const formatMoney = (value) => {
  if (value == null || typeof value === 'string' && value.trim() === '' || !Number.isFinite(Number(value))) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value))
}

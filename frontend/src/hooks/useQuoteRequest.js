import { useState } from 'react'
import { apiClient } from '../services/apiClient.js'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function useQuoteRequest() {
  const [form, setForm] = useState({ description: '', customerName: '', customerEmail: '' })
  const [errors, setErrors] = useState({})
  const [status, setStatus] = useState('idle')
  const [submitError, setSubmitError] = useState('')

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
  }

  function appendDescription(text) {
    setForm((current) => ({ ...current, description: current.description ? `${current.description} ${text}` : text }))
    setErrors((current) => ({ ...current, description: undefined }))
  }

  function validate() {
    const next = {}
    if (form.description.trim().length < 12) next.description = 'Add a little more detail about the piece you need.'
    if (!form.customerName.trim()) next.customerName = 'Please enter your name.'
    if (!EMAIL_PATTERN.test(form.customerEmail)) next.customerEmail = 'Enter a valid email address for the invoice.'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  async function submit() {
    if (!validate()) return null
    setStatus('loading')
    setSubmitError('')
    try {
      const quote = await apiClient.createQuote({
        description: form.description,
        customer: form.customerName,
        email: form.customerEmail,
        project: 'Two-door melamine wardrobe',
      })
      setStatus('success')
      return quote
    } catch (err) {
      setStatus('error')
      setSubmitError(err?.message || 'The quote could not be prepared. Please try again.')
      return null
    }
  }

  return { form, errors, status, submitError, updateField, appendDescription, submit }
}

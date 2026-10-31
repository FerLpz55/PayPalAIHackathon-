import { useState } from 'react'
import { requestQuote } from '../api/quoteApi.js'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function useQuoteRequest() {
  const [form, setForm] = useState({
    description: '',
    customerName: '',
    customerEmail: '',
  })
  const [errors, setErrors] = useState({})
  const [status, setStatus] = useState('idle')
  const [submitError, setSubmitError] = useState('')

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
  }

  function appendDescription(text) {
    setForm((current) => ({
      ...current,
      description: current.description ? `${current.description} ${text}` : text,
    }))
    setErrors((current) => ({ ...current, description: undefined }))
  }

  function validate() {
    const next = {}
    if (form.description.trim().length < 15) {
      next.description = 'Tell us a bit more about what you need.'
    }
    if (!form.customerName.trim()) {
      next.customerName = 'Please enter your name.'
    }
    if (!EMAIL_PATTERN.test(form.customerEmail)) {
      next.customerEmail = 'Please enter a valid email.'
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  async function submit() {
    if (!validate()) return null
    setStatus('loading')
    setSubmitError('')
    try {
      const quote = await requestQuote(form)
      setStatus('success')
      return quote
    } catch (error) {
      setStatus('error')
      setSubmitError(error.message)
      return null
    }
  }

  return { form, errors, status, submitError, updateField, appendDescription, submit }
}

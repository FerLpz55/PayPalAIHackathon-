import { useState } from 'react'
import { apiClient } from '../services/apiClient.js'

const MIN_LENGTH = 3
const MAX_LENGTH = 500

export function useAccountingAssistant() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  async function ask(rawQuestion = question) {
    const cleaned = rawQuestion.trim()
    if (cleaned.length < MIN_LENGTH) {
      setError('Write a slightly longer question.')
      return
    }
    if (cleaned.length > MAX_LENGTH) {
      setError(`Questions can be up to ${MAX_LENGTH} characters.`)
      return
    }
    setStatus('loading')
    setError('')
    try {
      const result = await apiClient.askAccountingAssistant(cleaned)
      setMessages((current) => [...current, { id: `${Date.now()}-${current.length}`, ...result }])
      setQuestion('')
      setStatus('idle')
    } catch (caught) {
      setStatus('error')
      setError(
        caught?.status === 503
          ? 'The AI assistant is not configured yet. Your totals are still available.'
          : caught?.message || 'The assistant could not answer. Please try again.',
      )
    }
  }

  return { question, setQuestion, messages, status, error, ask, maxLength: MAX_LENGTH }
}


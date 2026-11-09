import { useEffect, useRef, useState } from 'react'

function getSpeechRecognition() {
  return typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined
}

const DEFAULT_MESSAGE = 'Type a description, or tap Speak to use voice input.'

export function useSpeechInput(onText) {
  const [isListening, setIsListening] = useState(false)
  const [isSupported] = useState(() => Boolean(getSpeechRecognition()))
  const [message, setMessage] = useState(() => getSpeechRecognition() ? DEFAULT_MESSAGE : 'Type a description of the piece you need.')
  const recognitionRef = useRef(null)
  const heardRef = useRef(false)

  useEffect(() => () => {
    try {
      recognitionRef.current?.stop()
    } catch {
      // Recognition may already have ended while the form was unmounting.
    }
  }, [])

  function start() {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition || isListening) return
    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    heardRef.current = false
    recognition.onstart = () => setMessage('Listening… speak your project details.')
    recognition.onresult = (event) => {
      const text = Array.from(event.results)
        .filter((result) => result.isFinal !== false)
        .map((result) => result[0]?.transcript?.trim())
        .filter(Boolean)
        .join(' ')
      if (!text) {
        setMessage('No speech detected. You can try again or type your request.')
        return
      }
      heardRef.current = true
      onText(text)
      setMessage('Voice request added. Review it before continuing.')
    }
    recognition.onerror = (event) => {
      const messages = {
        'not-allowed': 'Microphone access was denied. Allow it in your browser settings or type your request.',
        'service-not-allowed': 'The browser speech service is unavailable. Type your request instead.',
        'audio-capture': 'No microphone is available. Connect one or type your request.',
        network: 'The browser speech service could not connect. Type your request or try again later.',
        'no-speech': 'No speech detected. You can try again or type your request.',
      }
      setIsListening(false)
      setMessage(messages[event?.error] || 'Voice input failed. Check microphone access or type your request.')
    }
    recognition.onend = () => {
      setIsListening(false)
      if (!heardRef.current) setMessage((current) => (current.startsWith('Listening') ? 'No speech detected. You can try again or type your request.' : current))
    }
    setIsListening(true)
    recognitionRef.current = recognition
    try {
      recognition.start()
    } catch {
      recognitionRef.current = null
      setIsListening(false)
      setMessage('Voice input failed to start. Check microphone access or type your request.')
    }
  }

  function stop() {
    recognitionRef.current?.stop()
  }

  return { isSupported, isListening, message, start, stop }
}

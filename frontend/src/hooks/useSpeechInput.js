import { useRef, useState } from 'react'

const SpeechRecognition =
  typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined

const DEFAULT_MESSAGE = 'Type a description, or tap Speak to use voice input.'

export function useSpeechInput(onText) {
  const [isListening, setIsListening] = useState(false)
  const [message, setMessage] = useState(SpeechRecognition ? DEFAULT_MESSAGE : 'Type a description of the piece you need.')
  const recognitionRef = useRef(null)
  const heardRef = useRef(false)

  function start() {
    if (!SpeechRecognition || isListening) return
    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    heardRef.current = false
    recognition.onstart = () => setMessage('Listening… speak your project details.')
    recognition.onresult = (event) => {
      const text = Array.from(event.results).map((result) => result[0].transcript).join(' ')
      heardRef.current = true
      onText(text)
      setMessage('Voice request added. Review it before continuing.')
    }
    recognition.onerror = () => setMessage('Voice input could not start. Check microphone access or type your request.')
    recognition.onend = () => {
      setIsListening(false)
      if (!heardRef.current) setMessage((current) => (current.startsWith('Listening') ? 'No speech detected. You can try again or type your request.' : current))
    }
    recognitionRef.current = recognition
    recognition.start()
    setIsListening(true)
  }

  function stop() {
    recognitionRef.current?.stop()
  }

  return { isSupported: Boolean(SpeechRecognition), isListening, message, start, stop }
}

import { useRef, useState } from 'react'

const SpeechRecognition =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : undefined

export function useSpeechInput(onText) {
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef(null)
  const isSupported = Boolean(SpeechRecognition)

  function start() {
    if (!isSupported || isListening) return
    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.onresult = (event) => {
      const text = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join(' ')
      onText(text)
    }
    recognition.onend = () => setIsListening(false)
    recognition.onerror = () => setIsListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setIsListening(true)
  }

  function stop() {
    recognitionRef.current?.stop()
  }

  return { isSupported, isListening, start, stop }
}

import { useEffect, useState } from 'react'

const readHash = () => window.location.hash.replace('#/', '').split('?')[0] || 'dashboard'

export function useHashRoute(onChange) {
  const [route, setRoute] = useState(readHash)

  useEffect(() => {
    const handleChange = () => {
      setRoute(readHash())
      onChange?.()
    }
    window.addEventListener('hashchange', handleChange)
    return () => window.removeEventListener('hashchange', handleChange)
  }, [onChange])

  const go = (next) => {
    window.location.hash = `/${next}`
    setRoute(next)
  }

  return { route, go }
}

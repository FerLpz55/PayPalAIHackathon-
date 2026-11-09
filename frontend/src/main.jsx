import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/index.css'
import App from './App.jsx'
import { adoptCustomerAccessFromUrl } from './services/sessionStore.js'

adoptCustomerAccessFromUrl()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

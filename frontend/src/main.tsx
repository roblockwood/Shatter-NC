import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/terminal.css'
import './index.css'
import App from './App.tsx'
import { BetaModeProvider } from './contexts/BetaModeContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BetaModeProvider>
      <App />
    </BetaModeProvider>
  </StrictMode>,
)

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/terminal.css'
import './index.css'
import App from './App.tsx'
import { BetaModeProvider } from './contexts/BetaModeContext'
import { IS_DEMO_MODE } from './config/demo'
import { installDemoFetch } from './demo/installDemoFetch'

if (IS_DEMO_MODE) {
  installDemoFetch()
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BetaModeProvider>
      <App />
    </BetaModeProvider>
  </StrictMode>,
)

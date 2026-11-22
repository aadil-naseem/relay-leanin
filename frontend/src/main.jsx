import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/big-shoulders-display/latin-700'
import '@fontsource/big-shoulders-display/latin-800'
import '@fontsource/big-shoulders-display/latin-900'
import '@fontsource/instrument-serif/latin-400'
import '@fontsource/instrument-serif/latin-400-italic'
import '@fontsource/ibm-plex-sans/latin-400'
import '@fontsource/ibm-plex-sans/latin-500'
import '@fontsource/ibm-plex-sans/latin-600'
import '@fontsource/ibm-plex-mono/latin-400'
import '@fontsource/ibm-plex-mono/latin-500'
import 'leaflet/dist/leaflet.css'
import './styles/tokens.css'
import './styles/base.css'
import './app/app-shell.css'
import './pages/Desk/desk.css'
import './pages/Exposure/exposure.css'
import './pages/WeakPoints/weak-points.css'
import './pages/WhatIf/what-if.css'
import './pages/Recovery/recovery.css'
import './pages/Partners/partners.css'
import './pages/Passports/passports.css'
import './pages/Passports/passports.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

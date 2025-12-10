import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './App.css'
import { validateEnvironment, logConfig } from './config/environment'

// Validate environment at startup
validateEnvironment()

// Log configuration in development
logConfig()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

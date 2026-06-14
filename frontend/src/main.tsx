import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import PrivacyPolicyPage from './pages/PrivacyPolicyPage.tsx'
import TermsPage from './pages/TermsPage.tsx'

document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') ?? 'dark')

const path = window.location.pathname
let root: React.ReactNode
if (path === '/privacy-policy') {
  root = <PrivacyPolicyPage />
} else if (path === '/terms') {
  root = <TermsPage />
} else {
  root = <App />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>{root}</StrictMode>,
)

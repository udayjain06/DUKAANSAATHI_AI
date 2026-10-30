import React, { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import TopNav from './components/TopNav'
import { Loader, Cursor, Background, ScrollProgress } from './components/Effects'
import { AuthProvider } from './context/AuthContext'
import { LanguageProvider } from './context/LanguageContext'
import { ThemeProvider } from './context/ThemeContext'
import Dashboard from './pages/Dashboard'
import SalesAnalysis from './pages/SalesAnalysis'
import Products from './pages/Products'
import Bills from './pages/Bills'
import Recommendations from './pages/Recommendations'
import Offers from './pages/Offers'
import MarginCalculator from './pages/MarginCalculator'
import Chat from './pages/Chat'
import Payment from './pages/Payment'
import Setup from './pages/Setup'
import Auth from './pages/Auth'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'auto' }) }, [pathname])
  return null
}

export default function App() {
  const [showLoader, setShowLoader] = useState(true)
  const [ready, setReady] = useState(false)

  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <BrowserRouter>
            <Background />
            <Cursor />
            <ScrollProgress />
            {showLoader && (
              <Loader onReveal={() => setReady(true)} onDone={() => setShowLoader(false)} />
            )}

            <div className="app-shell">
              <ScrollToTop />
              <TopNav />
              <main className="main-content">
                <div className="page-body">
                  {ready && (
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/sales" element={<SalesAnalysis />} />
                      <Route path="/products" element={<Products />} />
                      <Route path="/bills" element={<Bills />} />
                      <Route path="/recommendations" element={<Recommendations />} />
                      <Route path="/offers" element={<Offers />} />
                      <Route path="/margin" element={<MarginCalculator />} />
                      <Route path="/chat" element={<Chat />} />
                      <Route path="/payment" element={<Payment />} />
                      <Route path="/setup" element={<Setup />} />
                      <Route path="/auth" element={<Auth />} />
                    </Routes>
                  )}
                </div>
              </main>
              <footer className="site-footer">
                <span>DukaanSaathi AI v1.0 • Paytm Edition</span>
                <span>Paytm Build for India Hackathon</span>
              </footer>
            </div>
          </BrowserRouter>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  )
}

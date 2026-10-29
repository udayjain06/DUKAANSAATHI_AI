import React, { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
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

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className="main-content">
          <header className="page-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button
                className="btn btn-ghost btn-sm sidebar-toggle"
                onClick={() => setSidebarOpen(true)}
              >
                ☰
              </button>
              <h2>DukaanSaathi AI</h2>
            </div>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <a href="/recommendations" className="btn btn-outline btn-sm">
                💡 View Offers
              </a>
              <a href="/chat" className="btn btn-primary btn-sm">
                🤖 AI Chat
              </a>
            </div>
          </header>
          <div className="page-body">
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
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  )
}


import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

const NAV = [
  { path: '/', label: 'Dashboard', icon: '🏠' },
  { path: '/sales', label: 'Sales Analysis', icon: '📈' },
  { path: '/products', label: 'Products & Costs', icon: '📦' },
  { path: '/bills', label: 'Bill Upload', icon: '🧾' },
  { path: '/recommendations', label: 'Recommendations', icon: '💡' },
  { path: '/offers', label: 'Offers & Experiments', icon: '🎯' },
  { path: '/margin', label: 'Margin Calculator', icon: '🧮' },
  { path: '/chat', label: 'AI Assistant', icon: '🤖' },
  { path: '/payment', label: 'Subscription', icon: '💳' },
  { path: '/setup', label: 'Shop Setup', icon: '⚙️' },
]

export default function Sidebar({ open, onClose }) {
  const nav = useNavigate()
  const loc = useLocation()

  return (
    <>
      {open && (
        <div
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.3)',
            backdropFilter: 'blur(2px)',
            WebkitBackdropFilter: 'blur(2px)',
            zIndex: 99,
            animation: 'fade-in 200ms ease'
          }}
          onClick={onClose}
        />
      )}
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-logo">
          <h1>🛒 DukaanSaathi AI</h1>
          <p>Merchant Intelligence Platform</p>
        </div>
        <nav className="sidebar-nav">
          {NAV.map(item => (
            <div
              key={item.path}
              className={`nav-item ${loc.pathname === item.path ? 'active' : ''}`}
              onClick={() => { nav(item.path); onClose && onClose() }}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && (nav(item.path), onClose && onClose())}
            >
              <span style={{ fontSize: 17, lineHeight: 1 }}>{item.icon}</span>
              <span>{item.label}</span>
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          DukaanSaathi AI v1.0<br />
          Paytm Build for India Hackathon
        </div>
      </aside>
    </>
  )
}

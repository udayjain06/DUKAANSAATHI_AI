import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

// `short` is used in the top bar, `label` + `desc` in the mobile menu and feature tiles.
export const NAV = [
  { path: '/', short: 'Dashboard', label: 'Dashboard', icon: '🏠', desc: 'Your shop at a glance — revenue, best and worst days.' },
  { path: '/sales', short: 'Sales', label: 'Sales Analysis', icon: '📈', desc: 'Weekly trends, weak-day detection and product winners.' },
  { path: '/products', short: 'Products', label: 'Products & Costs', icon: '📦', desc: 'Manage your catalogue, cost prices and margins.' },
  { path: '/bills', short: 'Bills', label: 'Bill Upload', icon: '🧾', desc: 'Upload supplier bills and review the items.' },
  { path: '/recommendations', short: 'Suggestions', label: 'Recommendations', icon: '💡', desc: 'Offers suggested for your slowest days.' },
  { path: '/offers', short: 'Offers', label: 'Offers & Experiments', icon: '🎯', desc: 'Posters, WhatsApp copy and profit experiments.' },
  { path: '/margin', short: 'Margin', label: 'Margin Calculator', icon: '🧮', desc: 'Check any discount against your safety margin.' },
  { path: '/chat', short: 'AI Chat', label: 'AI Assistant', icon: '🤖', desc: 'Ask questions about your shop in Hindi or English.' },
  { path: '/payment', short: 'Plans', label: 'Subscription', icon: '💳', desc: 'Pick a plan and pay securely with Paytm.' },
  { path: '/setup', short: 'Setup', label: 'Shop Setup', icon: '⚙️', desc: 'Shop profile, language and margin rules.' },
]

export default function TopNav() {
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => { setOpen(false) }, [pathname])

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header className={`topbar ${scrolled ? 'scrolled' : ''}`}>
      <div className="topbar-inner">
        <Link to="/" className="brand" aria-label="DukaanSaathi AI home">
          <span className="brand-mark">D</span>
          <span className="brand-text">DukaanSaathi<em> AI</em></span>
        </Link>

        <nav className="topnav" aria-label="Main">
          {NAV.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${pathname === item.path ? 'active' : ''}`}
            >
              {item.short}
            </Link>
          ))}
        </nav>

        <div className="topbar-actions">
          <Link to="/recommendations" className="btn btn-outline btn-sm topbar-cta">Get offers</Link>
          <button
            className={`burger ${open ? 'open' : ''}`}
            onClick={() => setOpen(o => !o)}
            aria-label="Toggle menu"
            aria-expanded={open}
          >
            <i /><i /><i />
          </button>
        </div>
      </div>

      <div className={`menu-panel ${open ? 'open' : ''}`}>
        <div className="menu-grid">
          {NAV.map((item, i) => (
            <Link
              key={item.path}
              to={item.path}
              className={`menu-item ${pathname === item.path ? 'active' : ''}`}
              style={{ '--i': i }}
            >
              <span className="menu-icon">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </div>
      </div>
    </header>
  )
}

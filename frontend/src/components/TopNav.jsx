import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { useTheme } from '../context/ThemeContext'

export const NAV = [
  { path: '/', key: 'dashboard', short: 'Dashboard', label: 'Dashboard', icon: '🏠', desc: 'Your shop at a glance — revenue, best and worst days.' },
  { path: '/sales', key: 'sales', short: 'Sales', label: 'Sales Analysis', icon: '📈', desc: 'Weekly trends, weak-day detection and product winners.' },
  { path: '/products', key: 'products', short: 'Products', label: 'Products & Costs', icon: '📦', desc: 'Manage your catalogue, cost prices and margins.' },
  { path: '/bills', key: 'bills', short: 'Bills', label: 'Bill Upload', icon: '🧾', desc: 'Upload supplier bills and review the items.' },
  { path: '/recommendations', key: 'recommendations', short: 'Suggestions', label: 'Recommendations', icon: '💡', desc: 'Offers suggested for your slowest days.' },
  { path: '/offers', key: 'offers', short: 'Offers', label: 'Offers & Experiments', icon: '🎯', desc: 'Posters, WhatsApp copy and profit experiments.' },
  { path: '/margin', key: 'margin', short: 'Margin', label: 'Margin Calculator', icon: '🧮', desc: 'Check any discount against your safety margin.' },
  { path: '/chat', key: 'chat', short: 'AI Chat', label: 'AI Assistant', icon: '🤖', desc: 'Ask questions about your shop in Hindi or English.' },
  { path: '/payment', key: 'payment', short: 'Plans', label: 'Subscription', icon: '💳', desc: 'Pick a plan and pay securely with Paytm.' },
  { path: '/setup', key: 'setup', short: 'Setup', label: 'Shop Setup', icon: '⚙️', desc: 'Shop profile, language and margin rules.' },
]

export default function TopNav() {
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  const { user, signOut } = useAuth()
  const { lang, toggleLang, t } = useLanguage()
  const { theme, toggleTheme } = useTheme()

  useEffect(() => { setOpen(false) }, [pathname])

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const userInitial = user?.user_metadata?.full_name?.charAt(0) || user?.email?.charAt(0)?.toUpperCase() || 'U'

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
              {t(item.key) || item.short}
            </Link>
          ))}
        </nav>

        <div className="topbar-actions" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Theme switcher */}
          <button
            onClick={toggleTheme}
            className="btn btn-ghost btn-sm"
            style={{ padding: '5px 9px', borderRadius: 8, fontSize: 14 }}
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>

          {/* Language switcher */}
          <button
            onClick={toggleLang}
            className="btn btn-ghost btn-sm"
            style={{ padding: '5px 9px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}
            title="Switch Language"
            aria-label="Toggle Language"
          >
            {lang === 'en' ? 'हिन्दी' : 'EN'}
          </button>

          {/* Auth State */}
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div
                style={{
                  width: 30, height: 30, borderRadius: '50%',
                  background: 'var(--brand)', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13, fontWeight: 700,
                  boxShadow: 'var(--shadow-xs)'
                }}
                title={user.email}
              >
                {userInitial}
              </div>
              <button
                onClick={signOut}
                className="btn btn-ghost btn-sm"
                style={{ padding: '4px 8px', fontSize: 11.5, opacity: 0.85 }}
              >
                {t('logout')}
              </button>
            </div>
          ) : (
            <Link to="/auth" className="btn btn-primary btn-sm topbar-cta">
              {t('login')}
            </Link>
          )}

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
              <span>{t(item.key) || item.label}</span>
            </Link>
          ))}
          {!user ? (
            <Link to="/auth" className="menu-item" style={{ '--i': NAV.length }}>
              <span className="menu-icon">🔐</span>
              <span>{t('login')} / Sign Up</span>
            </Link>
          ) : (
            <div
              className="menu-item"
              style={{ '--i': NAV.length, cursor: 'pointer', color: 'var(--error)' }}
              onClick={signOut}
            >
              <span className="menu-icon">🚪</span>
              <span>{t('logout')} ({user.email})</span>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

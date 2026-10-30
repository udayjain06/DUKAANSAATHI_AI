import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { isSupabaseConfigured } from '../supabase'

export default function Auth() {
  const [mode, setMode] = useState('login') // 'login' | 'signup' | 'forgot'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)

  const { signIn, signUp, resetPassword } = useAuth()
  const { lang } = useLanguage()
  const nav = useNavigate()

  const isHindi = lang === 'hi'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)

    try {
      if (mode === 'signup') {
        await signUp(email, password, fullName)
        setMessage(isHindi ? 'खाता सफलतापूर्वक बन गया! डैशबोर्ड लोड हो रहा है...' : 'Account created successfully! Loading dashboard...')
        setTimeout(() => nav('/'), 800)
      } else if (mode === 'login') {
        await signIn(email, password)
        nav('/')
      } else if (mode === 'forgot') {
        await resetPassword(email)
        setMessage(isHindi ? 'पासवर्ड रीसेट लिंक आपके ईमेल पर भेजा गया है।' : 'Password reset link sent to your email.')
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 440, margin: '60px auto', padding: '0 16px' }}>
      <div className="card" style={{ padding: '32px 28px' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div className="brand-mark" style={{ width: 44, height: 44, fontSize: 22, margin: '0 auto 12px' }}>D</div>
          <h2 style={{ fontSize: 22, marginBottom: 6 }}>
            {mode === 'login' ? (isHindi ? 'Paytm AI में लॉगिन करें' : 'Sign in to Paytm AI') :
             mode === 'signup' ? (isHindi ? 'नया खाता बनाएं' : 'Create your account') :
             (isHindi ? 'पासवर्ड रीसेट करें' : 'Reset your password')}
          </h2>
          <p style={{ fontSize: 13, color: 'var(--muted)' }}>
            {isHindi ? 'सुरक्षित सुपबेस प्रमाणीकरण व डेटा गोपनीयता' : 'Secure Supabase authentication & data isolation'}
          </p>
        </div>

        {!isSupabaseConfigured() && (
          <div className="alert alert-info" style={{ fontSize: 12, marginBottom: 18 }}>
            <strong>Demo Mode:</strong> You can enter any demo credentials or configure <code>VITE_SUPABASE_URL</code> in <code>.env</code>.
          </div>
        )}

        {error && <div className="alert alert-error">{error}</div>}
        {message && <div className="alert alert-success">{message}</div>}

        {/* Tab switchers */}
        <div style={{ display: 'flex', background: 'var(--surface)', padding: 4, borderRadius: 10, marginBottom: 20 }}>
          <button
            type="button"
            className={`btn btn-sm ${mode === 'login' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ flex: 1, border: 'none', borderRadius: 7 }}
            onClick={() => { setMode('login'); setError(null); setMessage(null); }}
          >
            {isHindi ? 'लॉगिन' : 'Sign In'}
          </button>
          <button
            type="button"
            className={`btn btn-sm ${mode === 'signup' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ flex: 1, border: 'none', borderRadius: 7 }}
            onClick={() => { setMode('signup'); setError(null); setMessage(null); }}
          >
            {isHindi ? 'साइनअप' : 'Sign Up'}
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {mode === 'signup' && (
            <div className="form-group">
              <label className="form-label">{isHindi ? 'पूरा नाम' : 'Full Name'}</label>
              <input
                className="form-input"
                required
                placeholder="e.g. Rahul Sharma"
                value={fullName}
                onChange={e => setFullName(e.target.value)}
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label">{isHindi ? 'ईमेल पता' : 'Email Address'}</label>
            <input
              type="email"
              className="form-input"
              required
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
            />
          </div>

          {mode !== 'forgot' && (
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <label className="form-label" style={{ margin: 0 }}>{isHindi ? 'पासवर्ड' : 'Password'}</label>
                {mode === 'login' && (
                  <button
                    type="button"
                    onClick={() => { setMode('forgot'); setError(null); setMessage(null); }}
                    style={{ background: 'none', border: 'none', color: 'var(--accent)', fontSize: 12, cursor: 'pointer' }}
                  >
                    {isHindi ? 'पासवर्ड भूल गए?' : 'Forgot password?'}
                  </button>
                )}
              </div>
              <input
                type="password"
                className="form-input"
                required
                minLength={6}
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 8 }}
            disabled={loading}
          >
            {loading ? (isHindi ? 'सत्यापित हो रहा है...' : 'Verifying...') :
             mode === 'login' ? (isHindi ? 'लॉगिन करें' : 'Sign In') :
             mode === 'signup' ? (isHindi ? 'खाता बनाएं' : 'Create Account') :
             (isHindi ? 'रीसेट लिंक भेजें' : 'Send Reset Link')}
          </button>

          {mode === 'forgot' && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={{ width: '100%', marginTop: 10 }}
              onClick={() => { setMode('login'); setError(null); setMessage(null); }}
            >
              {isHindi ? '← लॉगिन पर वापस जाएं' : '← Back to Sign In'}
            </button>
          )}
        </form>
      </div>
    </div>
  )
}


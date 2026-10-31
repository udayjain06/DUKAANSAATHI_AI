import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

export default function Auth() {
  const [mode, setMode] = useState('login') // 'login' | 'signup' | 'forgot'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [shopName, setShopName] = useState('')
  const [shopType, setShopType] = useState('kirana')
  const [loading, setLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)

  const { signIn, signUp, signInDemo, resetPassword } = useAuth()
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
        await signUp(email, password, fullName, shopName, shopType)
        setMessage(
          isHindi
            ? 'खाता सफलतापूर्वक बन गया! आपका नया डैशबोर्ड लोड हो रहा है...'
            : 'Account created successfully! Loading your fresh dashboard...'
        )
        setTimeout(() => nav('/'), 600)
      } else if (mode === 'login') {
        await signIn(email, password)
        nav('/')
      } else if (mode === 'forgot') {
        await resetPassword(email)
        setMessage(
          isHindi
            ? 'पासवर्ड रीसेट लिंक आपके ईमेल पर भेजा गया है।'
            : 'Password reset link sent to your email.'
        )
      }
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
      if (!err.response || err.code === 'ERR_NETWORK' || status === 404) {
        setError(
          isHindi
            ? 'सर्वर से संपर्क नहीं हो पा रहा है। कृपया एक मिनट बाद पुनः प्रयास करें।'
            : 'Cannot reach the server. Please try again in a minute.'
        )
      } else if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail)) {
        setError(detail.map(d => d.msg || d).join(', '))
      } else {
        setError(err.message || 'Authentication failed. Please check credentials.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDemoLogin = async () => {
    setDemoLoading(true)
    setError(null)
    try {
      await signInDemo()
      nav('/')
    } catch (err) {
      const status = err.response?.status
      if (!err.response || err.code === 'ERR_NETWORK' || status === 404) {
        setError(
          isHindi
            ? 'सर्वर से संपर्क नहीं हो पा रहा है। कृपया एक मिनट बाद पुनः प्रयास करें।'
            : 'Cannot reach the server. Please try again in a minute.'
        )
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load demo environment')
      }
    } finally {
      setDemoLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 460, margin: '50px auto', padding: '0 16px' }}>
      <div className="card" style={{ padding: '32px 28px' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div className="brand-mark" style={{ width: 48, height: 48, fontSize: 24, margin: '0 auto 12px' }}>D</div>
          <h2 style={{ fontSize: 22, marginBottom: 6 }}>
            {mode === 'login' ? (isHindi ? 'दुकानसाथी में लॉगिन करें' : 'Sign in to DukaanSaathi AI') :
             mode === 'signup' ? (isHindi ? 'अपनी दुकान का नया खाता बनाएं' : 'Create your Shop Account') :
             (isHindi ? 'पासवर्ड रीसेट करें' : 'Reset your password')}
          </h2>
          <p style={{ fontSize: 13, color: 'var(--muted)' }}>
            {isHindi ? 'व्यक्तिगत खाता, सुरक्षित डेटा पृथक्करण एवं AI विश्लेषण' : 'Individual shop accounts with strict data isolation'}
          </p>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
        {message && <div className="alert alert-success" style={{ marginBottom: 16 }}>{message}</div>}

        {/* Tab switchers */}
        <div style={{ display: 'flex', background: 'var(--surface)', padding: 4, borderRadius: 10, marginBottom: 20 }}>
          <button
            type="button"
            className={`btn btn-sm ${mode === 'login' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ flex: 1, border: 'none', borderRadius: 7 }}
            onClick={() => { setMode('login'); setError(null); setMessage(null); }}
          >
            {isHindi ? 'लॉगिन (Sign In)' : 'Sign In'}
          </button>
          <button
            type="button"
            className={`btn btn-sm ${mode === 'signup' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ flex: 1, border: 'none', borderRadius: 7 }}
            onClick={() => { setMode('signup'); setError(null); setMessage(null); }}
          >
            {isHindi ? 'साइनअप (Register)' : 'Register'}
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {mode === 'signup' && (
            <>
              <div className="form-group">
                <label className="form-label">{isHindi ? 'दुकानदार का नाम' : 'Shopkeeper Name'}</label>
                <input
                  className="form-input"
                  required
                  placeholder="e.g. Rajesh Kumar"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">{isHindi ? 'दुकान का नाम' : 'Shop / Store Name'}</label>
                <input
                  className="form-input"
                  required
                  placeholder="e.g. Kumar General Store"
                  value={shopName}
                  onChange={e => setShopName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">{isHindi ? 'दुकान का प्रकार' : 'Shop Type'}</label>
                <select
                  className="form-input"
                  value={shopType}
                  onChange={e => setShopType(e.target.value)}
                >
                  <option value="kirana">{isHindi ? 'किराना / ग्रोसरी (Kirana / Grocery)' : 'Kirana / Grocery Store'}</option>
                  <option value="bakery">{isHindi ? 'बेकरी / कन्फेक्शनरी (Bakery)' : 'Bakery & Confectionery'}</option>
                </select>
              </div>
            </>
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
            disabled={loading || demoLoading}
          >
            {loading ? (isHindi ? 'सत्यापित हो रहा है...' : 'Verifying...') :
             mode === 'login' ? (isHindi ? 'लॉगिन करें' : 'Sign In') :
             mode === 'signup' ? (isHindi ? 'नया खाता बनाएं' : 'Create Fresh Account') :
             (isHindi ? 'रीसेट लिंक भेजें' : 'Send Reset Link')}
          </button>
        </form>

        {/* Demo Account Button */}
        <div style={{ marginTop: 24, paddingTop: 20, borderTop: '1px solid var(--border)', textAlign: 'center' }}>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>
            {isHindi ? 'तुरंत डेमो स्टोर और नमूना डेटा देखना चाहते हैं?' : 'Want to explore pre-loaded demo data & analytics?'}
          </p>
          <button
            type="button"
            className="btn btn-ghost"
            style={{ width: '100%', border: '1px dashed var(--border)', fontSize: 13 }}
            onClick={handleDemoLogin}
            disabled={loading || demoLoading}
          >
            {demoLoading ? 'Loading Demo Store...' : '⚡ Try Demo Store (Sharma General Store)'}
          </button>
        </div>
      </div>
    </div>
  )
}

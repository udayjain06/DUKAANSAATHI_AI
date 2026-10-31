import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Area, AreaChart, PieChart, Pie
} from 'recharts'
import api, { fmt, pct } from '../api'
import { Loading, ErrorMsg, Badge, DataLabel, SyntheticBanner, Modal } from '../components/UI'
import { Reveal, CountUp } from '../components/Effects'
import { NAV } from '../components/TopNav'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

const LIME = '#00BAF2'
const ACCENT = '#002970'
const GREEN = '#10B981'
const RED = '#EF4444'
const WEEKDAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const chartTooltipStyle = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  boxShadow: '0 12px 32px rgba(0,0,0,0.3)',
  fontSize: 13,
  padding: '8px 12px',
  color: 'var(--text)',
}

const CATEGORY_COLORS = ['#00BAF2', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#6366F1', '#14B8A6']

const RING_R = 34
const RING_C = 2 * Math.PI * RING_R

export default function Dashboard() {
  const { user } = useAuth()
  const { t, lang } = useLanguage()
  const [data, setData] = useState(null)
  const [userDash, setUserDash] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [ringOn, setRingOn] = useState(false)

  // Add Transaction Modal state
  const [showTxModal, setShowTxModal] = useState(false)
  const [txForm, setTxForm] = useState({
    description: '',
    amount: '',
    type: 'expense',
    category: 'auto'
  })
  const [submittingTx, setSubmittingTx] = useState(false)
  const [txFeedback, setTxFeedback] = useState(null)

  const loadData = () => {
    Promise.all([
      api.get('/sales/summary?weeks=8'),
      api.get('/insights/dashboard'),
      api.get('/recommendation/pending'),
      api.get('/user/dashboard').catch(() => ({ data: null }))
    ])
      .then(([s, d, r, u]) => {
        setData({ sales: s.data, dash: d.data, pending: r.data })
        if (u?.data) setUserDash(u.data)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadData()
  }, [user])

  useEffect(() => {
    if (!data) return undefined
    const tTimer = setTimeout(() => setRingOn(true), 500)
    return () => clearTimeout(tTimer)
  }, [data])

  const handleCreateTx = async (e) => {
    e.preventDefault()
    if (!txForm.description || !txForm.amount) return
    setSubmittingTx(true)
    setTxFeedback(null)

    try {
      const res = await api.post('/user/transactions', {
        description: txForm.description,
        amount: parseFloat(txForm.amount),
        type: txForm.type,
        category: txForm.category === 'auto' ? undefined : txForm.category
      })

      setTxFeedback({
        type: 'success',
        msg: `Transaction saved! Category: ${res.data.category} ${res.data.is_anomaly ? '(⚠️ Flagged Anomaly)' : '✓'}`
      })

      // Refresh user dashboard data
      const uRes = await api.get('/user/dashboard')
      setUserDash(uRes.data)

      setTxForm({ description: '', amount: '', type: 'expense', category: 'auto' })
      setTimeout(() => {
        setShowTxModal(false)
        setTxFeedback(null)
      }, 1400)
    } catch (err) {
      setTxFeedback({ type: 'error', msg: err.response?.data?.detail || err.message })
    } finally {
      setSubmittingTx(false)
    }
  }

  if (!user && !loading) {
    return (
      <div style={{ maxWidth: 540, margin: '60px auto', textAlign: 'center', padding: '0 20px' }}>
        <div className="card" style={{ padding: '40px 32px' }}>
          <div className="brand-mark" style={{ width: 56, height: 56, fontSize: 28, margin: '0 auto 16px' }}>D</div>
          <h2 style={{ fontSize: 24, marginBottom: 8, color: 'var(--heading)' }}>Welcome to DukaanSaathi AI</h2>
          <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
            Empower your shop with AI retail analytics, profit protection, weak-day offers, and smart ML predictions.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Link to="/auth" className="btn btn-primary" style={{ padding: '12px' }}>
              Sign In to Your Shop
            </Link>
            <button
              onClick={() => {
                api.post('/auth/demo').then(res => {
                  if (res.data?.token) {
                    localStorage.setItem('dukaansaathi_auth_token', res.data.token)
                    window.location.reload()
                  }
                })
              }}
              className="btn btn-ghost"
              style={{ padding: '12px', border: '1px solid var(--border)' }}
            >
              ⚡ Explore Demo Store (Sharma General Store)
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (loading) return <Loading text={t('loading')} />
  if (error) return <ErrorMsg message={error} />
  if (!data) return null

  const { sales, dash, pending } = data
  const weeklyData = (sales.weekly || []).map(w => ({
    name: w.week?.slice(-5) || w.week,
    revenue: Math.round(w.revenue),
    txns: w.txns,
  }))
  const weekdayData = WEEKDAY_ORDER
    .filter(d => sales.weekday_avg?.[d] !== undefined)
    .map(d => ({
      name: d.slice(0, 3),
      avg: Math.round(sales.weekday_avg[d] || 0),
      isWeak: dash.weak_day?.weekday?.slice(0, 3) === d.slice(0, 3),
    }))
  const topProducts = dash.products?.top || []
  const weakDay = dash.weak_day
  const dip = Math.min(Math.abs(Number(weakDay?.dip_pct) || 0), 100)
  const pendingCount = dash.pending_recommendations || 0

  const axis = { fontSize: 12, fill: 'var(--muted)' }

  // User financials & ML predictions
  const financials = userDash?.financials || { balance: 0, total_income: 0, total_expense: 0, savings_rate_pct: 0 }
  const predictions = userDash?.ml_predictions || { predicted_7day_spending: 0, predicted_30day_spending: 0, trend: 'new', confidence_score: 0 }
  const categoriesData = (userDash?.categories || []).map(c => ({ name: c.category, value: Math.round(c.total_amount || c.amount || 0) }))
  const recentUserTxns = userDash?.recent_transactions || []

  return (
    <div className="home">
      {/* ───────────── ONBOARDING GUIDE FOR NEW SHOPS ───────────── */}
      {(!sales.total_revenue && recentUserTxns.length === 0) && (
        <div className="card" style={{
          marginBottom: 24,
          padding: '24px',
          background: 'linear-gradient(135deg, rgba(0, 186, 242, 0.08), rgba(0, 41, 112, 0.12))',
          border: '1px solid rgba(0, 186, 242, 0.3)',
          borderRadius: 16
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 32 }}>🏪</span>
            <div style={{ flex: 1, minWidth: 260 }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 6px', color: 'var(--heading)' }}>
                {lang === 'hi' ? 'दुकानसाथी AI में आपका स्वागत है!' : 'Welcome to DukaanSaathi AI!'}
              </h3>
              <p style={{ fontSize: 13, color: 'var(--muted)', margin: '0 0 16px', lineHeight: 1.5 }}>
                {lang === 'hi'
                  ? 'आपकी दुकान का व्यक्तिगत खाता तैयार है। AI भविष्यवाणी और मुनाफ़ा विश्लेषण शुरू करने के लिए ये कदम उठाएं:'
                  : 'Your business workspace is set up and strictly isolated. Get started in 3 quick steps to unlock AI insights:'}
              </p>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <Link to="/products" className="btn btn-primary btn-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>📦</span> 1. {lang === 'hi' ? 'उत्पाद जोड़ें' : 'Add Products'}
                </Link>
                <Link to="/bills" className="btn btn-ghost btn-sm" style={{ border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>🧾</span> 2. {lang === 'hi' ? 'होलसेल बिल अपलोड करें' : 'Upload Bills'}
                </Link>
                <button onClick={() => setShowTxModal(true)} className="btn btn-ghost btn-sm" style={{ border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>💳</span> 3. {lang === 'hi' ? 'बिक्री / खर्च दर्ज करें' : 'Record Transaction'}
                </button>
                <Link to="/setup" className="btn btn-ghost btn-sm" style={{ border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>⚙️</span> {lang === 'hi' ? 'दुकान सेटिंग्स' : 'Shop Setup'}
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ───────────── USER FINANCIAL & ML HUB ───────────── */}
      <section className="section" style={{ paddingTop: 0, marginBottom: 28 }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
          marginBottom: 16,
          padding: '16px 22px',
          background: 'var(--surface)',
          borderRadius: 16,
          border: '1px solid var(--border)'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 18 }}>💳</span>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: 'var(--heading)' }}>
                {t('userLedger')}
              </h2>
              <span style={{
                fontSize: 11,
                background: 'rgba(0, 186, 242, 0.15)',
                color: '#00BAF2',
                padding: '2px 8px',
                borderRadius: 99,
                fontWeight: 600
              }}>
                {user ? user.email : 'Demo Account (RLS Isolated)'}
              </span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: 12.5, color: 'var(--muted)' }}>
              Real-time balance, scikit-learn ML spending predictions & IsolationForest anomaly detection.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={() => setShowTxModal(true)}
              className="btn btn-primary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <span>+</span> {t('addTransaction')}
            </button>
            <Link to="/chat" className="btn btn-ghost btn-sm">
              💬 Ask Groq AI
            </Link>
          </div>
        </div>

        {/* Financial Stat Bento */}
        <div className="bento" style={{ marginBottom: 20 }}>
          <Reveal className="block block-light" delay={0}>
            <div className="block-title">{t('currentBalance')}</div>
            <div className="block-num" style={{ color: '#00BAF2' }}>
              <CountUp value={financials.balance} format={n => fmt(n)} />
            </div>
            <div className="block-sub">Available Funds</div>
          </Reveal>

          <Reveal className="block" delay={60}>
            <div className="block-title">{t('monthlyIncome')}</div>
            <div className="block-num green">
              <CountUp value={financials.total_income} format={n => fmt(n)} />
            </div>
            <div className="block-sub">Earned this month</div>
          </Reveal>

          <Reveal className="block" delay={120}>
            <div className="block-title">{t('monthlyExpenses')}</div>
            <div className="block-num red">
              <CountUp value={financials.total_expense} format={n => fmt(n)} />
            </div>
            <div className="block-sub">Spent this month</div>
          </Reveal>

          <Reveal className="block block-violet" delay={180}>
            <div className="block-title">🔮 ML 30-Day Spending</div>
            <div className="block-num">
              <CountUp value={predictions.predicted_30day_spending} format={n => fmt(n)} />
            </div>
            <div className="block-sub">Ridge Regressor ({predictions.trend})</div>
          </Reveal>
        </div>

        {/* Anomaly & ML Insight Banner */}
        {userDash?.anomalies_count > 0 && (
          <Reveal className="alert alert-warning" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20 }}>⚠️</span>
            <div style={{ flex: 1 }}>
              <strong>{t('anomalyAlert')}:</strong> scikit-learn IsolationForest flagged {userDash.anomalies_count} unusual transaction(s) requiring review.
            </div>
            <span className="badge badge-blocked">Unusual Pattern</span>
          </Reveal>
        )}

        {/* ML Spending & Category Graphs Grid */}
        <div className="split" style={{ marginBottom: 24 }}>
          {/* Monthly Trend / Income vs Expense */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>Income vs Expenses Trend</h3>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>Past 4 Months</span>
            </div>
            <div className="card-body">
              <div style={{ width: '100%', height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={userDash?.monthly_trend || []} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="month" tick={axis} axisLine={false} tickLine={false} />
                    <YAxis tick={axis} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                    <Tooltip formatter={v => fmt(v)} contentStyle={chartTooltipStyle} />
                    <Bar dataKey="income" name="Income" fill={GREEN} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="expense" name="Expense" fill={RED} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Category Breakdown */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>{t('spendingByCategory')}</h3>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>ML Auto-Classified</span>
            </div>
            <div className="card-body">
              {categoriesData.length === 0 ? (
                <p style={{ color: 'var(--muted)', fontSize: 13, textAlign: 'center', padding: 30 }}>No expense categories yet.</p>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ width: 140, height: 140 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={categoriesData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={38}
                          outerRadius={62}
                        >
                          {categoriesData.map((e, index) => (
                            <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={v => fmt(v)} contentStyle={chartTooltipStyle} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ flex: 1, maxHeight: 150, overflowY: 'auto', paddingRight: 6 }}>
                    {categoriesData.map((cat, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, marginBottom: 6 }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ width: 8, height: 8, borderRadius: '50%', background: CATEGORY_COLORS[idx % CATEGORY_COLORS.length] }} />
                          {cat.name}
                        </span>
                        <strong style={{ color: 'var(--heading)' }}>{fmt(cat.value)}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Recent Ledger Transactions */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700 }}>{t('recentTransactions')}</h3>
            <button onClick={() => setShowTxModal(true)} className="btn btn-ghost btn-sm">
              + Add New
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div style={{ overflowX: 'auto' }}>
              <table className="table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--muted)' }}>
                    <th style={{ padding: '10px 16px' }}>Date</th>
                    <th style={{ padding: '10px 16px' }}>Description</th>
                    <th style={{ padding: '10px 16px' }}>Category</th>
                    <th style={{ padding: '10px 16px' }}>Type</th>
                    <th style={{ padding: '10px 16px', textAlign: 'right' }}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {recentUserTxns.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ padding: 24, textAlign: 'center', color: 'var(--muted)' }}>
                        No transactions recorded yet. Click "+ Add Transaction" above!
                      </td>
                    </tr>
                  ) : (
                    recentUserTxns.slice(0, 6).map((tx) => (
                      <tr key={tx.id} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '10px 16px', color: 'var(--muted)', whiteSpace: 'nowrap' }}>{tx.date}</td>
                        <td style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--heading)' }}>
                          {tx.description}
                          {tx.is_anomaly && (
                            <span style={{
                              marginLeft: 8,
                              fontSize: 10,
                              background: 'rgba(239, 68, 68, 0.15)',
                              color: '#EF4444',
                              padding: '2px 6px',
                              borderRadius: 4,
                              fontWeight: 700
                            }}>
                              ⚠️ Anomaly
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '10px 16px' }}>
                          <span style={{
                            fontSize: 11,
                            padding: '2px 8px',
                            background: 'var(--surface-2)',
                            borderRadius: 6,
                            color: 'var(--text)'
                          }}>
                            {tx.category}
                          </span>
                        </td>
                        <td style={{ padding: '10px 16px' }}>
                          <span style={{
                            fontSize: 11,
                            fontWeight: 700,
                            color: tx.type === 'income' ? GREEN : RED,
                            textTransform: 'uppercase'
                          }}>
                            {tx.type}
                          </span>
                        </td>
                        <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: tx.type === 'income' ? GREEN : 'var(--heading)' }}>
                          {tx.type === 'income' ? '+' : '-'}{fmt(tx.amount)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────── HERO ───────────── */}
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow hero-eyebrow">{t('merchantIntelligence')}</div>
          <h1 className="hero-title" aria-label="Never miss a weak day in your shop again">
            Never miss a <span style={{ color: '#00BAF2' }}>weak day</span> in your shop again
          </h1>
          <p className="hero-sub">
            {t('heroTag')}
          </p>
          <div className="hero-cta">
            <Link to="/recommendations" className="btn btn-primary btn-lg">{t('getOffers')}</Link>
            <div className="hero-note">
              <b>8 weeks</b>
              of sales analysed
            </div>
          </div>
          <div className="hero-chips">
            <span>UPI</span><span>Paytm QR</span><span>WhatsApp Status</span>
          </div>
        </div>

        <div className="hero-visual">
          <div className="hero-card">
            <div className="hc-pill">
              <span className="hc-pill-icon">✦</span>
              <div>
                <b>{pendingCount} pending {pendingCount === 1 ? 'action' : 'actions'}</b>
                <small>Recommendations waiting</small>
              </div>
            </div>

            <div className="hc-top">
              <div className="hc-label">{t('totalRevenue')}</div>
              <div className="hc-value"><CountUp value={sales.total_revenue} format={n => fmt(n)} /></div>
              <div className="hc-sub">Avg {fmt(sales.avg_daily_revenue)} / day</div>
            </div>

            <div className="hc-mid">
              <Link to="/sales" className="btn btn-primary btn-sm">{t('salesAnalysis')}</Link>
              <Link to="/products" className="btn btn-dark-outline btn-sm">{t('products')}</Link>
            </div>

            <div className="hc-bottom">
              <div className="hc-ring">
                <svg viewBox="0 0 80 80" width="84" height="84">
                  <circle cx="40" cy="40" r={RING_R} className="ring-track" />
                  <circle
                    cx="40" cy="40" r={RING_R}
                    className="ring-fill"
                    strokeDasharray={RING_C}
                    strokeDashoffset={ringOn ? RING_C * (1 - dip / 100) : RING_C}
                    transform="rotate(-90 40 40)"
                  />
                </svg>
                <span>{weakDay ? `${Math.round(dip)}%` : '—'}</span>
              </div>
              <div className="hc-copy">
                <div className="hc-label hc-label-lime">{t('weakDay')}</div>
                <b>{weakDay ? weakDay.weekday : t('noneDetected')}</b>
                <small>{weakDay ? 'Sales dip vs. average' : 'Your week looks steady'}</small>
                <Link to="/recommendations" className="hc-btn">Get report</Link>
              </div>
            </div>

            <span className="hc-badge hc-cal">📅</span>
            <span className="hc-badge hc-rupee">₹</span>
          </div>
        </div>
      </section>

      <Reveal className="hero-banner"><SyntheticBanner /></Reveal>

      {/* ───────────── AT A GLANCE ───────────── */}
      <section className="section">
        <Reveal>
          <div className="section-head">
            <div className="eyebrow">{t('atAGlance')}</div>
            <h2>{t('yourShopInSimpleBlocks')}</h2>
            <p>{t('numbersThatMatter')}</p>
          </div>
        </Reveal>

        <div className="bento">
          <Reveal className="block b-chart" delay={0}>
            <div className="block-title">{t('revenueTrend')}</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={weeklyData} margin={{ top: 10, right: 8, left: -8, bottom: 0 }}>
                  <defs>
                    <linearGradient id="limeGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00BAF2" stopOpacity={0.28} />
                      <stop offset="95%" stopColor="#00BAF2" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 6" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="name" tick={axis} axisLine={false} tickLine={false} />
                  <YAxis tick={axis} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                  <Tooltip formatter={v => fmt(v)} contentStyle={chartTooltipStyle} cursor={{ stroke: 'var(--border)' }} />
                  <Area type="monotone" dataKey="revenue" stroke="#00BAF2" strokeWidth={3} fill="url(#limeGrad)"
                    dot={{ r: 4, fill: '#00BAF2', strokeWidth: 3, stroke: 'var(--surface)' }}
                    activeDot={{ r: 7, fill: '#00BAF2', stroke: 'var(--surface)', strokeWidth: 3 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Reveal>

          <Reveal className="block block-light" delay={80}>
            <div className="block-title">{t('transactions')}</div>
            <div className="block-num"><CountUp value={sales.total_txns || 0} /></div>
            <div className="block-sub">Across 8 weeks</div>
          </Reveal>

          <Reveal className="block" delay={140}>
            <div className="block-title">{t('bestDay')}</div>
            <div className="block-num green">{sales.best_day || '—'}</div>
            <div className="block-sub">Avg {fmt(sales.weekday_avg?.[sales.best_day])}</div>
          </Reveal>

          <Reveal className="block" delay={200}>
            <div className="block-title">{t('worstDay')}</div>
            <div className="block-num red">{sales.worst_day || '—'}</div>
            <div className="block-sub">Dip {pct(weakDay?.dip_pct)}</div>
          </Reveal>

          <Reveal className="block block-violet" delay={260}>
            <div className="block-title">{t('pendingActions')}</div>
            <div className="block-num"><CountUp value={pendingCount} /></div>
            <Link to="/recommendations" className="block-link">{t('review')}</Link>
          </Reveal>
        </div>
      </section>

      {/* ───────────── PATTERNS ───────────── */}
      <section className="section">
        <Reveal>
          <div className="section-head">
            <div className="eyebrow">Weekly pattern</div>
            <h2>Which days carry your shop?</h2>
            <p>The weak day is highlighted in red.</p>
          </div>
        </Reveal>

        <div className="bento">
          <Reveal className="block b-chart">
            <div className="block-title">Weekday average revenue</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={weekdayData} barSize={34} margin={{ top: 10, right: 8, left: -8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 6" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="name" tick={axis} axisLine={false} tickLine={false} />
                  <YAxis tick={axis} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                  <Tooltip formatter={v => fmt(v)} contentStyle={chartTooltipStyle} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                  <Bar dataKey="avg" radius={[10, 10, 4, 4]}>
                    {weekdayData.map((e, i) => (
                      <Cell key={i} fill={e.isWeak ? RED : '#00BAF2'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Reveal>

          <Reveal className="block block-dark b-wide" delay={80}>
            <div className="block-head">
              <div className="block-title">⚠️ Weak day opportunity</div>
              {weakDay && <Badge status={weakDay.confidence} />}
            </div>
            {weakDay ? (
              <>
                <div className="mini-stats">
                  <div><span>Day</span><b className="red">{weakDay.weekday}</b></div>
                  <div><span>Sales dip</span><b className="red">{pct(weakDay.dip_pct)}</b></div>
                  <div><span>Consistency</span><b>{weakDay.consistency}</b></div>
                </div>
                <p className="block-text">
                  Based on an 8-week consistent pattern (not statistical significance). An offer on{' '}
                  <strong>{weakDay.weekday}</strong> could reduce this gap.
                </p>
              </>
            ) : (
              <p className="block-text">No weak day detected yet.</p>
            )}
          </Reveal>

          <Reveal className="block block-lime" delay={140}>
            <div className="block-title">Active offers</div>
            <div className="block-num"><CountUp value={dash.active_offers || 0} /></div>
            <div className="block-sub">Running now</div>
          </Reveal>

          <Reveal className="block block-light" delay={200}>
            <div className="block-title">Check a discount</div>
            <div className="block-sub" style={{ marginTop: 10 }}>See if an offer keeps your margin safe.</div>
            <Link to="/margin" className="block-link">Open calculator →</Link>
          </Reveal>
        </div>
      </section>

      {/* ───────────── PRODUCTS & ACTIONS ───────────── */}
      <section className="section">
        <Reveal>
          <div className="section-head">
            <div className="eyebrow">Products & actions</div>
            <h2>What sells, and what to do next</h2>
          </div>
        </Reveal>

        <div className="split">
          <Reveal className="block">
            <div className="block-title">🏆 Top products</div>
            {topProducts.length === 0 && <p className="block-text">No product data yet.</p>}
            {topProducts.map(p => (
              <div key={p.product_id} className="list-item">
                <div>
                  <div className="li-name">{p.name}</div>
                  <div className="li-sub">{p.total_units} units sold</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="li-amount">{fmt(p.total_revenue)}</div>
                  {p.margin_pct != null && <div className="li-sub">{pct(p.margin_pct)} margin</div>}
                </div>
              </div>
            ))}
          </Reveal>

          <Reveal className="block" delay={100}>
            <div className="block-head">
              <div className="block-title">💡 Pending recommendations</div>
              <Link to="/recommendations" className="block-link inline">See all →</Link>
            </div>
            {(!pending || pending.length === 0) && <p className="block-text">Nothing pending — you're all caught up.</p>}
            {(pending || []).slice(0, 3).map(r => (
              <div key={r.id} className="reco-mini">
                <div className="reco-mini-top">
                  <span className="reco-day">📅 {r.weak_day}</span>
                  <span className="reco-dip">↓{pct(r.dip_pct)} dip</span>
                  <DataLabel label={r.data_label} />
                  <span style={{ marginLeft: 'auto' }}><Badge status={r.margin?.status || 'ok'} /></span>
                </div>
                <p>{r.explanation?.[lang] || r.explanation?.en || 'View details for the full recommendation.'}</p>
              </div>
            ))}
          </Reveal>
        </div>
      </section>

      {/* ───────────── ALL TOOLS NAVIGATION ───────────── */}
      <section className="section">
        <Reveal>
          <div className="section-head">
            <div className="eyebrow">Everything in one place</div>
            <h2>All your tools, one scroll away</h2>
            <p>Pick any tool below — or use the menu at the top.</p>
          </div>
        </Reveal>

        <div className="tiles">
          {NAV.filter(n => n.path !== '/').map((n, i) => (
            <Reveal key={n.path} delay={(i % 3) * 90}>
              <Link to={n.path} className="tile">
                <span className="tile-icon">{n.icon}</span>
                <span className="tile-title">{t(n.key) || n.label}</span>
                <span className="tile-desc">{n.desc}</span>
                <span className="tile-arrow">↗</span>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ───────────── ADD TRANSACTION MODAL ───────────── */}
      {showTxModal && (
        <Modal
          title={t('addTransaction')}
          onClose={() => setShowTxModal(false)}
          footer={
            <>
              <button className="btn btn-ghost" onClick={() => setShowTxModal(false)}>{t('cancel')}</button>
              <button className="btn btn-primary" onClick={handleCreateTx} disabled={submittingTx || !txForm.description || !txForm.amount}>
                {submittingTx ? 'Saving...' : t('save')}
              </button>
            </>
          }
        >
          <form onSubmit={handleCreateTx} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {txFeedback && (
              <div className={`alert alert-${txFeedback.type === 'error' ? 'danger' : 'success'}`}>
                {txFeedback.msg}
              </div>
            )}
            <div>
              <label className="form-label">{t('description')} *</label>
              <input
                className="form-input"
                placeholder="e.g. Swiggy lunch, Petrol refill, Grocery wholesale..."
                value={txForm.description}
                onChange={e => setTxForm({ ...txForm, description: e.target.value })}
                required
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label className="form-label">{t('amount')} (₹) *</label>
                <input
                  type="number"
                  step="any"
                  className="form-input"
                  placeholder="0.00"
                  value={txForm.amount}
                  onChange={e => setTxForm({ ...txForm, amount: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="form-label">{t('type')}</label>
                <select
                  className="form-input"
                  value={txForm.type}
                  onChange={e => setTxForm({ ...txForm, type: e.target.value })}
                >
                  <option value="expense">Expense (खर्च)</option>
                  <option value="income">Income (आय)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="form-label">{t('category')}</label>
              <select
                className="form-input"
                value={txForm.category}
                onChange={e => setTxForm({ ...txForm, category: e.target.value })}
              >
                <option value="auto">✨ Auto-Detect via Machine Learning (TF-IDF + LogisticRegression)</option>
                <option value="Food">Food (भोजन)</option>
                <option value="Groceries">Groceries (किराना)</option>
                <option value="Travel">Travel / Fuel (यात्रा / पेट्रोल)</option>
                <option value="Utilities">Utilities / Bills (बिजली / पानी)</option>
                <option value="Shopping">Shopping (खरीदारी)</option>
                <option value="Healthcare">Healthcare (दवा / डॉक्टर)</option>
                <option value="Entertainment">Entertainment (मनोरंजन)</option>
                <option value="Salary">Salary / Income (वेतन / कमाई)</option>
                <option value="Supplies">Store Supplies (दुकान का सामान)</option>
              </select>
            </div>
            <p style={{ fontSize: 11.5, color: 'var(--muted)', margin: 0 }}>
              💡 All transactions are saved to your isolated profile with automatic anomaly scoring.
            </p>
          </form>
        </Modal>
      )}
    </div>
  )
}
